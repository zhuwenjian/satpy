#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2016

# Author(s):

#   Martin Raspaud <martin.raspaud@smhi.se>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""MultiScene object to blend satellite data.
"""

import logging
import numpy as np
import dask
import dask.array as da
import xarray as xr
import pandas as pd
from satpy.scene import Scene
from satpy.writers import get_enhanced_image
from satpy.dataset import combine_metadata, DatasetID
from itertools import chain

try:
    # new API
    from dask.highlevelgraph import HighLevelGraph
except ImportError:
    # old API
    import dask.sharedict as HighLevelGraph

try:
    from itertools import zip_longest
except ImportError:
    # python 2.7
    from itertools import izip_longest as zip_longest

try:
    import imageio
except ImportError:
    imageio = None

log = logging.getLogger(__name__)


def cascaded_compute(callback, arrays, batch_size=None, optimize=True):
    """Dask helper function for iterating over computed dask arrays.

    Args:
        callback (callable): Called with a single numpy array computed from
                             the provided dask arrays.
        arrays (list, tuple): Dask arrays to pass to callback.
        batch_size (int): Group computation in to this many arrays at a time.
        optimize (bool): Whether to try to optimize the dask graphs of the
                         provided arrays.

    Returns: `dask.Delayed` object to be computed

    """
    def _callback_wrapper(arr, previous_call, cb=callback):
        del previous_call  # used only for task ordering
        return cb(arr)

    array_batches = []
    if not batch_size:
        array_batches.append(arrays)
    else:
        arr_gens = iter(arrays)
        array_batches = (arrs for arrs in zip_longest(*([arr_gens] * batch_size)))

    for batch_arrs in array_batches:
        batch_arrs = [x for x in batch_arrs if x is not None]
        if optimize:
            # optimize Dask graph over all objects
            dsk = da.Array.__dask_optimize__(
                # combine all Dask Array graphs
                HighLevelGraph.merge(*[e.__dask_graph__() for e in batch_arrs]),
                # get Dask Array keys in result
                list(dask.core.flatten([e.__dask_keys__() for e in batch_arrs]))
            )
            # rebuild Dask Arrays
            batch_arrs = [da.Array(dsk, e.name, e.chunks, e.dtype) for e in batch_arrs]

        current_write = None
        for dask_arr in batch_arrs:
            current_write = dask.delayed(_callback_wrapper)(
                dask_arr, current_write)
        yield current_write


def stack(datasets):
    """First dataset at the bottom."""
    base = datasets[0].copy()
    for dataset in datasets[1:]:
        base = base.where(dataset.isnull(), dataset)
    return base


def timeseries(datasets):
    """Expands dataset with and concats by time dimension"""
    expanded_ds = []
    for ds in datasets:
        tmp = ds.expand_dims("time")
        tmp.coords["time"] = pd.DatetimeIndex([ds.attrs["start_time"]])
        expanded_ds.append(tmp)

    res = xr.concat(expanded_ds, dim="time")
    res.attrs = combine_metadata(*[x.attrs for x in expanded_ds])
    return res


class _SceneGenerator(object):
    """Fancy way of caching Scenes from a generator."""

    def __init__(self, scene_gen):
        self._scene_gen = scene_gen
        self._scene_cache = []
        self._dataset_idx = {}
        # this class itself is not an iterator, make one
        self._self_iter = self._create_cached_iter()

    @property
    def first(self):
        """First element in the generator."""
        return next(iter(self))

    def _create_cached_iter(self):
        """Iterate over the provided scenes, caching them for later."""
        for scn in self._scene_gen:
            self._scene_cache.append(scn)
            yield scn

    def __iter__(self):
        """Iterate over the provided scenes, caching them for later."""
        idx = 0
        while True:
            if idx >= len(self._scene_cache):
                try:
                    scn = next(self._self_iter)
                except StopIteration:
                    return
            else:
                scn = self._scene_cache[idx]
            yield scn
            idx += 1

    def __getitem__(self, ds_id):
        """Get a specific dataset from the scenes."""
        for scn in self:
            yield scn.get(ds_id)


class MultiScene(object):
    """Container for multiple `Scene` objects."""

    def __init__(self, scenes=None):
        """Initialize MultiScene and validate sub-scenes.

        Args:
            scenes (iterable):
                `Scene` objects to operate on (optional)

        .. note::

            If the `scenes` passed to this object are a generator then certain
            operations performed will try to preserve that generator state.
            This may limit what properties or methods are available to the
            user. To avoid this behavior compute the passed generator by
            converting the passed scenes to a list first:
            ``MultiScene(list(scenes))``.

        """
        self._scenes = scenes or []
        scenes = iter(self._scenes)
        self._scene_gen = _SceneGenerator(iter(scenes))
        # if we were originally given a generator-like object then we want to
        # coordinate the loading between _SceneGenerator and _scenes
        # otherwise it doesn't really matter and other operations may prefer
        # a list
        if not isinstance(scenes, (list, tuple)):
            self._scenes = iter(self._scene_gen)

    @property
    def first_scene(self):
        """First Scene of this MultiScene object."""
        return self._scene_gen.first

    @classmethod
    def from_files(cls, files_to_sort, reader=None, **kwargs):
        """Create multiple Scene objects from multiple files.

        This uses the :func:`satpy.readers.group_files` function to group
        files. See this function for more details on possible keyword
        arguments.

        .. versionadded:: 0.12

        """
        from satpy.readers import group_files
        file_groups = group_files(files_to_sort, reader=reader, **kwargs)
        scenes = (Scene(filenames=fg) for fg in file_groups)
        return cls(scenes)

    def __iter__(self):
        """Iterate over the provided Scenes once."""
        for scn in self._scenes:
            yield scn

    @property
    def scenes(self):
        """Get list of Scene objects contained in this MultiScene.

        .. note::

            If the Scenes contained in this object are stored in a
            generator (not list or tuple) then accessing this property
            will load/iterate through the generator possibly

        """
        if self.is_generator:
            log.debug("Forcing iteration of generator-like object of Scenes")
            self._scenes = list(self._scenes)
        return self._scenes

    @property
    def is_generator(self):
        """Contained Scenes are stored as a generator."""
        return not isinstance(self._scenes, (list, tuple))

    @property
    def loaded_dataset_ids(self):
        """Union of all Dataset IDs loaded by all children."""
        return set(ds_id for scene in self.scenes for ds_id in scene.keys())

    @property
    def shared_dataset_ids(self):
        """Dataset IDs shared by all children."""
        shared_ids = set(self.scenes[0].keys())
        for scene in self.scenes[1:]:
            shared_ids &= set(scene.keys())
        return shared_ids

    def _all_same_area(self, dataset_ids):
        """Return True if all areas for the provided IDs are equal."""
        all_areas = []
        for ds_id in dataset_ids:
            for scn in self.scenes:
                ds = scn.get(ds_id)
                if ds is None:
                    continue
                all_areas.append(ds.attrs.get('area'))
        all_areas = [area for area in all_areas if area is not None]
        return all(all_areas[0] == area for area in all_areas[1:])

    @property
    def all_same_area(self):
        return self._all_same_area(self.loaded_dataset_ids)

    @staticmethod
    def _call_scene_func(gen, func_name, create_new_scene, *args, **kwargs):
        """Abstract method for running a Scene method on each Scene."""
        for scn in gen:
            new_scn = getattr(scn, func_name)(*args, **kwargs)
            if create_new_scene:
                yield new_scn
            else:
                yield scn

    def _generate_scene_func(self, gen, func_name, create_new_scene, *args, **kwargs):
        """Abstract method for running a Scene method on each Scene.

        Additionally, modifies current MultiScene or creates a new one if needed.
        """
        new_gen = self._call_scene_func(gen, func_name, create_new_scene, *args, **kwargs)
        new_gen = new_gen if self.is_generator else list(new_gen)
        if create_new_scene:
            return self.__class__(new_gen)
        self._scene_gen = _SceneGenerator(new_gen)
        self._scenes = iter(self._scene_gen)

    def load(self, *args, **kwargs):
        """Load the required datasets from the multiple scenes."""
        self._generate_scene_func(self._scenes, 'load', False, *args, **kwargs)

    def resample(self, destination=None, **kwargs):
        """Resample the multiscene."""
        return self._generate_scene_func(self._scenes, 'resample', True, destination=destination, **kwargs)

    def blend(self, blend_function=stack):
        """Blend the datasets into one scene.

        .. note::

            Blending is not currently optimized for generator-based
            MultiScene.

        """
        new_scn = Scene()
        common_datasets = self.shared_dataset_ids
        for ds_id in common_datasets:
            datasets = [scn[ds_id] for scn in self.scenes if ds_id in scn]
            new_scn[ds_id] = blend_function(datasets)

        return new_scn

    def _get_animation_info(self, all_datasets, filename, fill_value=None):
        """Determine filename and shape of animation to be created."""
        valid_datasets = [ds for ds in all_datasets if ds is not None]
        first_dataset = valid_datasets[0]
        last_dataset = valid_datasets[-1]
        first_img = get_enhanced_image(first_dataset)
        first_img_data = first_img.finalize(fill_value=fill_value)[0]
        shape = tuple(first_img_data.sizes.get(dim_name)
                      for dim_name in ('y', 'x', 'bands'))
        if fill_value is None and filename.endswith('gif'):
            log.warning("Forcing fill value to '0' for GIF Luminance images")
            fill_value = 0
            shape = shape[:2]

        attrs = first_dataset.attrs.copy()
        if 'end_time' in last_dataset.attrs:
            attrs['end_time'] = last_dataset.attrs['end_time']
        this_fn = filename.format(**attrs)
        return this_fn, shape, fill_value

    def _get_animation_frames(self, all_datasets, shape, fill_value=None,
                              ignore_missing=False):
        """Create enhanced image frames to save to a file."""
        for idx, ds in enumerate(all_datasets):
            if ds is None and ignore_missing:
                continue
            elif ds is None:
                log.debug("Missing frame: %d", idx)
                data = da.zeros(shape, dtype=np.uint8, chunks=shape)
                data = xr.DataArray(data)
            else:
                img = get_enhanced_image(ds)
                data, mode = img.finalize(fill_value=fill_value)
                if data.ndim == 3:
                    # assume all other shapes are (y, x)
                    # we need arrays grouped by pixel so
                    # transpose if needed
                    data = data.transpose('y', 'x', 'bands')
            yield data.data

    def _distribute_frame_compute(self, writers, frame_keys, frames_to_write, client, batch_size=1):
        """Use ``dask.distributed`` to compute multiple frames at a time."""
        from queue import Queue
        from threading import Thread

        def load_data(frame_gen, q):
            for frame_arrays in frame_gen:
                future_list = client.compute(frame_arrays)
                for frame_key, arr_future in zip(frame_keys, future_list):
                    q.put({frame_key: arr_future})
            q.put(None)

        input_q = Queue(batch_size if batch_size is not None else 1)
        load_thread = Thread(target=load_data, args=(frames_to_write, input_q,))
        remote_q = client.gather(input_q)
        load_thread.start()

        while True:
            future_dict = remote_q.get()
            if future_dict is None:
                break

            # write the current frame
            # this should only be one element in the dictionary, but this is
            # also the easiest way to get access to the data
            for frame_key, result in future_dict.items():
                # frame_key = rev_future_dict[future]
                w = writers[frame_key]
                w.append_data(result)
            input_q.task_done()

        log.debug("Waiting for child thread...")
        load_thread.join(10)
        if load_thread.is_alive():
            import warnings
            warnings.warn("Background thread still alive after failing to die gracefully")
        else:
            log.debug("Child thread died successfully")

    def _simple_frame_compute(self, writers, frame_keys, frames_to_write):
        """Compute frames the plain dask way."""
        for frame_arrays in frames_to_write:
            for frame_key, product_frame in zip(frame_keys, frame_arrays):
                w = writers[frame_key]
                w.append_data(product_frame.compute())

    def save_animation(self, filename, datasets=None, fps=10, fill_value=None,
                       batch_size=1, ignore_missing=False, client=True, **kwargs):
        """Helper method for saving to movie (MP4) or GIF formats.

        Supported formats are dependent on the `imageio` library and are
        determined by filename extension by default.

        .. note::

            Starting with ``imageio`` 2.5.0, the use of FFMPEG depends on
            a separate ``imageio-ffmpeg`` package.

        By default all datasets available will be saved to individual files
        using the first Scene's datasets metadata to format the filename
        provided. If a dataset is not available from a Scene then a black
        array is used instead (np.zeros(shape)).

        This function can use the ``dask.distributed`` library for improved
        performance by computing multiple frames at a time (see `batch_size`
        option below). If the distributed library is not available then frames
        will be generated one at a time, one product at a time.

        Args:
            filename (str): Filename to save to. Can include python string
                            formatting keys from dataset ``.attrs``
                            (ex. "{name}_{start_time:%Y%m%d_%H%M%S.gif")
            datasets (list): DatasetIDs to save (default: all datasets)
            fps (int): Frames per second for produced animation
            fill_value (int): Value to use instead creating an alpha band.
            batch_size (int): Number of frames to compute at the same time.
                This only has affect if the `dask.distributed` package is
                installed. This will default to 1. Setting this to 0 or less
                will attempt to process all frames at once. This option should
                be used with care to avoid memory issues when trying to
                improve performance. Note that this is the total number of
                frames for all datasets, so when saving 2 datasets this will
                compute ``(batch_size / 2)`` frames for the first dataset and
                ``(batch_size / 2)`` frames for the second dataset.
            ignore_missing (bool): Don't include a black frame when a dataset
                                   is missing from a child scene.
            client (bool or dask.distributed.Client): Dask distributed client
                to use for computation. If this is ``True`` (default) then
                any existing clients will be used or a new one created.
                If this is ``False`` or ``None`` then a client will not be
                created and ``dask.distributed`` will not be used. If this
                is a dask ``Client`` object then it will be used for
                distributed computation.
            kwargs: Additional keyword arguments to pass to
                   `imageio.get_writer`.

        """
        if imageio is None:
            raise ImportError("Missing required 'imageio' library")

        scene_gen = self._scene_gen
        first_scene = self.first_scene
        scenes = iter(self._scene_gen)
        info_scenes = [first_scene]
        if 'end_time' in filename:
            # if we need the last scene to generate the filename
            # then compute all the scenes so we can figure it out
            log.debug("Generating scenes to compute end_time for filename")
            scenes = list(scenes)
            info_scenes.append(scenes[-1])

        available_ds = [first_scene.datasets.get(ds) for ds in first_scene.wishlist]
        available_ds = [DatasetID.from_dict(ds.attrs) for ds in available_ds if ds is not None]
        dataset_ids = datasets or available_ds

        if not dataset_ids:
            raise RuntimeError("No datasets found for saving (resampling may be needed to generate composites)")

        # writers = []
        writers = {}
        # delayeds = []
        frames = {}
        for dataset_id in dataset_ids:
            if not self.is_generator and not self._all_same_area([dataset_id]):
                raise ValueError("Sub-scene datasets must all be on the same "
                                 "area (see the 'resample' method).")

            all_datasets = scene_gen[dataset_id]
            info_datasets = [scn.get(dataset_id) for scn in info_scenes]
            this_fn, shape, this_fill = self._get_animation_info(info_datasets, filename, fill_value=fill_value)
            data_to_write = self._get_animation_frames(all_datasets, shape, this_fill, ignore_missing)

            writer = imageio.get_writer(this_fn, fps=fps, **kwargs)
            frames[dataset_id] = data_to_write
            # delayeds.append(data_to_write)
            # delayed = cascaded_compute(writer.append_data, data_to_write, batch_size=batch_size)
            # Save delayeds and writers to compute and close later
            # delayeds.append(delayed)
            writers[dataset_id] = writer

        client = client or None  # convert False/None to None
        close_client = False
        if client is True:
            try:
                # get existing client
                from dask.distributed import get_client
                client = get_client()
            except ImportError:
                log.debug("'dask.distributed' library was not found, will "
                          "use simple frame processing.")
            except ValueError:
                # create new client
                from dask.distributed import Client
                client = Client()
                close_client = True

        # get an ordered list of frames
        frame_keys, frames_to_write = list(zip(*frames.items()))
        frames_to_write = zip(*frames_to_write)
        if client is not None:
            self._distribute_frame_compute(writers, frame_keys, frames_to_write, client, batch_size=batch_size)
        else:
            self._simple_frame_compute(writers, frame_keys, frames_to_write)

        for writer in writers.values():
            writer.close()
        if close_client:
            log.debug("Closing dask client...")
            client.close()


def no_op(x):
    return x