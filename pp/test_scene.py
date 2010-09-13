"""Unit tests for scene.py.
"""

import ConfigParser
import pp.projector
import string

def random_string(length, choices = string.letters):
    """Generates a random string with elements from *set* of the specified
    *length*.
    """
    import random
    return "".join([random.choice(choices)
                    for i in range(length)])
EPSILON = 0.0001
DUMMY_STRING = "test_plugin"

def patch_configparser():
    """Patch to fake ConfigParser.
    """
    class FakeConfigParser:
        """Dummy ConfigParser class.
        """
        def __init__(self, *args, **kwargs):
            pass
        
        def read(self, *args, **kwargs):
            """Dummy read method
            """
            del args, kwargs
            self = self

        def get(self, *args, **kwargs):
            """Dummy get method
            """
            del args, kwargs
            self = self
            return DUMMY_STRING
        
    ConfigParser._ConfigParser = ConfigParser.ConfigParser
    ConfigParser.ConfigParser = FakeConfigParser

def unpatch_configparser():
    """Unpatch fake ConfigParser.
    """
    ConfigParser.ConfigParser = ConfigParser._ConfigParser
    delattr(ConfigParser, "_ConfigParser")


def patch_projector():
    """Patch to fake projector.
    """
    class FakeProjector:
        """Dummy Projector class.
        """
        def __init__(self, *args, **kwargs):
            pass

        def project_array(self, arg):
            """Dummy project_array method.
            """
            self = self
            return arg

        def dummy(self):
            """Dummy method to get pylint happy.
            """
            self = self

    pp.projector._Projector = pp.projector.Projector
    pp.projector.Projector = FakeProjector

def unpatch_projector():
    """Unpatch fake projector
    """
    pp.projector.Projector = pp.projector._Projector
    delattr(pp.projector, "_Projector")



import unittest
from pp.scene import SatelliteScene, SatelliteInstrumentScene
from pp.channel import NotLoadedError
import datetime
import numpy as np


class TestSatelliteScene(unittest.TestCase):
    """Class for testing the SatelliteScene class.
    """

    scene = None

    def test_init(self):
        """Creation of a satellite scene.
        """

        self.scene = SatelliteScene()
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assert_(self.scene.time_slot is None)
        self.assert_(self.scene.orbit is None)
        self.assert_(self.scene.area_id is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)

        # time_slot

        time_slot = datetime.datetime.now()

        self.scene = SatelliteScene(time_slot = time_slot)
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assertEquals(self.scene.time_slot, time_slot)
        self.assert_(self.scene.orbit is None)
        self.assert_(self.scene.area_id is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)

        self.assertRaises(TypeError,
                          SatelliteScene,
                          time_slot = random_string(4))
        
        self.assertRaises(TypeError,
                          SatelliteScene,
                          time_slot = np.random.uniform(1000))
        
        self.assertRaises(TypeError,
                          SatelliteScene,
                          time_slot = int(np.random.uniform(1000)))

        self.assertRaises(TypeError,
                          SatelliteScene,
                          time_slot = [])

        # area_id

        area_id = random_string(int(np.random.uniform(9)) + 1)

        self.scene = SatelliteScene(area_id = area_id)
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assertEquals(self.scene.area_id, area_id)
        self.assert_(self.scene.orbit is None)
        self.assert_(self.scene.time_slot is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)

        self.assertRaises(TypeError,
                          SatelliteScene,
                          area_id = np.random.uniform(1000))
        
        self.assertRaises(TypeError,
                          SatelliteScene,
                          area_id = int(np.random.uniform(1000)))

        self.assertRaises(TypeError,
                          SatelliteScene,
                          area_id = [])


        
        # orbit

        orbit = random_string(int(np.random.uniform(9)) + 1)

        self.scene = SatelliteScene(orbit = orbit)
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assertEquals(self.scene.orbit, orbit)
        self.assert_(self.scene.area_id is None)
        self.assert_(self.scene.time_slot is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)

        self.assertRaises(TypeError,
                          SatelliteScene,
                          orbit = np.random.uniform(1000))
        
        self.assertRaises(TypeError,
                          SatelliteScene,
                          orbit = int(np.random.uniform(1000)))

        self.assertRaises(TypeError,
                          SatelliteScene,
                          orbit = [])


    def test_fullname(self):
        """Fullname of a sat scene.
        """
        self.scene = SatelliteScene()

        self.scene.satname = random_string(int(np.random.uniform(9)) + 1)
        self.scene.number = random_string(int(np.random.uniform(9)) + 1)
        self.scene.variant = random_string(int(np.random.uniform(9)) + 1)
        self.assertEquals(self.scene.fullname,
                          self.scene.variant +
                          self.scene.satname +
                          self.scene.number)
        
class TestSatelliteInstrumentScene(unittest.TestCase):
    """Class for testing the SatelliteInstrumentScene class.
    """

    scene = None

    def setUp(self):
        """Patch foreign modules.
        """
        patch_configparser()
        patch_projector()

    def test_init_area(self):
        """Creation of a satellite instrument scene.
        """
        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels
        # area_id

        area_id = random_string(int(np.random.uniform(9)) + 1)

        self.scene = SatelliteInstrumentScene2(area_id = area_id)
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assertEquals(self.scene.area_id, area_id)
        self.assert_(self.scene.orbit is None)
        self.assert_(self.scene.time_slot is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)
        self.assert_(self.scene.instrument_name is None)
        self.assertEquals(self.scene.channels_to_load, set([]))
        for i, chn in enumerate(self.scene.channels):
            self.assertEquals(chn.name, channels[i][0])
            self.assertEquals(chn.wavelength_range, channels[i][1])
            self.assertEquals(chn.resolution, channels[i][2])

        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          area_id = np.random.uniform(1000))
        
        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          area_id = int(np.random.uniform(1000)))

        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          area_id = [])




        
    def test_init_orbit(self):
        """Creation of a satellite instrument scene.
        """
        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels

        
        # orbit

        orbit = random_string(int(np.random.uniform(9)) + 1)

        self.scene = SatelliteInstrumentScene2(orbit = orbit)
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assertEquals(self.scene.orbit, orbit)
        self.assert_(self.scene.area_id is None)
        self.assert_(self.scene.time_slot is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)
        self.assert_(self.scene.instrument_name is None)
        self.assertEquals(self.scene.channels_to_load, set([]))
        for i, chn in enumerate(self.scene.channels):
            self.assertEquals(chn.name, channels[i][0])
            self.assertEquals(chn.wavelength_range, channels[i][1])
            self.assertEquals(chn.resolution, channels[i][2])

        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          orbit = np.random.uniform(1000))
        
        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          orbit = int(np.random.uniform(1000)))

        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          orbit = [])

        
    def test_init_time_slot(self):
        """Creation of a satellite instrument scene.
        """
        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels
        
        # time_slot

        time_slot = datetime.datetime.now()

        self.scene = SatelliteInstrumentScene2(time_slot = time_slot)
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assertEquals(self.scene.time_slot, time_slot)
        self.assert_(self.scene.orbit is None)
        self.assert_(self.scene.area_id is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)
        self.assert_(self.scene.instrument_name is None)
        self.assertEquals(self.scene.channels_to_load, set([]))
        for i, chn in enumerate(self.scene.channels):
            self.assertEquals(chn.name, channels[i][0])
            self.assertEquals(chn.wavelength_range, channels[i][1])
            self.assertEquals(chn.resolution, channels[i][2])

        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          time_slot = random_string(4))
        
        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          time_slot = np.random.uniform(1000))
        
        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          time_slot = int(np.random.uniform(1000)))

        self.assertRaises(TypeError,
                          SatelliteInstrumentScene2,
                          time_slot = [])

        
        
    def test_init(self):
        """Creation of a satellite instrument scene.
        """

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels

        self.scene = SatelliteInstrumentScene2()
        self.assertEquals(self.scene.satname, "")
        self.assertEquals(self.scene.number, "")
        self.assert_(self.scene.time_slot is None)
        self.assert_(self.scene.orbit is None)
        self.assert_(self.scene.area_id is None)
        self.assert_(self.scene.lat is None)
        self.assert_(self.scene.lon is None)
        self.assert_(self.scene.instrument_name is None)
        self.assertEquals(self.scene.channels_to_load, set([]))
        for i, chn in enumerate(self.scene.channels):
            self.assertEquals(chn.name, channels[i][0])
            self.assertEquals(chn.wavelength_range, channels[i][1])
            self.assertEquals(chn.resolution, channels[i][2])



    def test_getitem(self):
        """__getitem__ for sat scenes.
        """

        # empty scene
        self.scene = SatelliteInstrumentScene()        

        self.assertRaises(KeyError, self.scene.__getitem__,
                          np.random.uniform(100))
        self.assertRaises(KeyError, self.scene.__getitem__,
                          int(np.random.uniform(10000)))
        self.assertRaises(KeyError, self.scene.__getitem__,
                          random_string(4))

        # scene with 3 channels

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels

        self.scene = SatelliteInstrumentScene2()
        for chn in channels:
            self.assertEquals(self.scene[chn[0]].name, chn[0])
            for i in range(3):
                self.assertEquals(self.scene[chn[1][i]].wavelength_range[i],
                                  chn[1][i])
            self.assertEquals(self.scene[chn[2]].resolution, chn[2])
            self.assertEquals(self.scene[(chn[0], chn[2])].name, chn[0])

        self.assertRaises(KeyError, self.scene.__getitem__, [])
        self.assertRaises(KeyError, self.scene.__getitem__, random_string(5))
        self.assertRaises(TypeError, self.scene.__getitem__, set([]))
        self.assertRaises(KeyError, self.scene.__getitem__, 5.0)

        self.assertEquals(len(self.scene.__getitem__(5000, aslist = True)), 2)

        chans = self.scene.__getitem__(5000, aslist = True)
        self.assertEquals(self.scene[chans[0].name].name, channels[1][0])
        self.assertEquals(self.scene[chans[1].name].name, channels[2][0])

    def test_check_channels(self):
        """Check loaded channels.
        """

        # No data loaded

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels

        self.scene = SatelliteInstrumentScene2()
        for chn in channels:
            self.assertRaises(NotLoadedError, self.scene.check_channels, chn[0])
            self.assertRaises(NotLoadedError, self.scene.check_channels, chn[2])
            for i in range(3):
                self.assertRaises(NotLoadedError,
                                  self.scene.check_channels,
                                  chn[1][i])

        # With data
        
        self.scene[0.7] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[11.5] = np.ma.array(np.random.rand(3, 3),
                                       mask = np.array(np.random.rand(3, 3) * 2,
                                                       dtype = int))
        self.assertTrue(self.scene.check_channels(0.7, 6.4, 11.5))
        self.assertRaises(KeyError, self.scene.check_channels, random_string(5))

    def test_loaded_channels(self):
        """Loaded channels list.
        """
        # No data loaded

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            channel_list = channels

        self.scene = SatelliteInstrumentScene2()
        self.assertEquals(self.scene.loaded_channels(), set([]))
        
        # With data
        
        self.scene[0.7] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[11.5] = np.ma.array(np.random.rand(3, 3),
                                       mask = np.array(np.random.rand(3, 3) * 2,
                                                       dtype = int))

    def test_project(self):
        """Projecting a scene.
        """
        area_id = random_string(8)
        area_id2 = random_string(8)
        # scene with 3 channels

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            instrument_name = random_string(8)
            channel_list = channels

        # case of a swath

        self.scene = SatelliteInstrumentScene2(area_id=None)

        # With data
        
        self.scene[0.7] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4].area_id = area_id
        
        res = self.scene.project(area_id2)
        self.assertEquals(res[0.7].shape, (3, 3))
        self.assertEquals(res[6.4].shape, (3, 3))
        self.assertRaises(KeyError, res.__getitem__, 11.5)

        res = self.scene.project(area_id2, channels=[0.7])
        self.assertEquals(res[0.7].shape, (3, 3))
        self.assertRaises(KeyError, res.__getitem__, 6.4)

        res = self.scene.project(area_id2, channels=[0.7, 11.5])
        self.assertEquals(res[0.7].shape, (3, 3))
        self.assertRaises(KeyError, res.__getitem__, 11.5)


        res = self.scene.project(area_id2, channels=[area_id])
        self.assertRaises(KeyError, res.__getitem__, 0.7)

        self.assertRaises(TypeError, self.scene.project,
                          area_id2, channels=11.5)



        # case of a grid

        self.scene = SatelliteInstrumentScene2(area_id=area_id)

        # With data
        
        self.scene[0.7] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[11.5] = np.ma.array(np.random.rand(3, 3),
                                       mask = np.array(np.random.rand(3, 3) * 2,
                                                       dtype = int))

        
        res = self.scene.project(area_id2)
        self.assertEquals(res[11.5].shape, (3, 3))
        
        res = self.scene.project(area_id2, channels=[0.7])
        self.assertEquals(res[0.7].shape, (3, 3))
        self.assertRaises(KeyError, res.__getitem__, 6.4)

        self.scene[6.4].area_id = area_id2

        res = self.scene.project(area_id2)
        self.assertEquals(res[0.7].shape, (3, 3))
        
        # case of self projection

        self.scene = SatelliteInstrumentScene2(area_id=area_id)

        # With data
        
        self.scene[0.7] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[11.5] = np.ma.array(np.random.rand(3, 3),
                                       mask = np.array(np.random.rand(3, 3) * 2,
                                                       dtype = int))

        self.scene[6.4].area_id = area_id
        
        res = self.scene.project(area_id)
        self.assertEquals(res[0.7].shape, (3, 3))
        self.assertEquals(res[6.4].shape, (3, 3))
        self.assertEquals(res[11.5].shape, (3, 3))
        
        res = self.scene.project(area_id, channels=[0.7])
        self.assertEquals(res[0.7].shape, (3, 3))
        self.assertEquals(res[6.4].shape, (3, 3))
        self.assertEquals(res[11.5].shape, (3, 3))
        
        
    def test_load(self):
        """Loading channels into a scene.
        """

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            instrument_name = random_string(8)
            channel_list = channels

        self.scene = SatelliteInstrumentScene2()

        self.assertRaises(TypeError, self.scene.load, "00_7")

        self.scene.load(["00_7"])
        self.assertEquals(set(["00_7"]), self.scene.channels_to_load)

        self.scene = SatelliteInstrumentScene2()
        self.scene.load()
        self.assertEquals(set(["00_7", "06_4", "11_5"]),
                          self.scene.channels_to_load)

        self.scene.load(["CTTH"])
        

    def test_get_lat_lon(self):
        """Getting lats and lons of a scene.
        """
        area_id = random_string(8)
        # scene with 3 channels

        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            instrument_name = random_string(8)
            channel_list = channels

        # case of a swath

        self.scene = SatelliteInstrumentScene2(area_id=None)

        (lat, lon) = self.scene.get_lat_lon(1000)

        self.assertTrue(lat is not None)
        self.assertTrue(lon is not None)
        
        numb = np.random.uniform(100000)
        self.assertRaises(TypeError, self.scene.get_lat_lon, numb)

        # case of a grid

        self.scene = SatelliteInstrumentScene2(area_id=area_id)

        (lat, lon) = self.scene.get_lat_lon(1000)

        self.assertTrue(lat is not None)
        self.assertTrue(lon is not None)

        numb = np.random.uniform(100000)
        self.assertRaises(TypeError, self.scene.get_lat_lon, numb)

        

    def test_assemble_swaths(self):
        """Assembling swaths in a single satscene object.
        """
        channels = [["00_7", (0.5, 0.7, 0.9), 2500],
                    ["06_4", (5.7, 6.4, 7.1), 5000],
                    ["11_5", (10.5, 11.5, 12.5), 5000]]

        class SatelliteInstrumentScene2(SatelliteInstrumentScene):
            """Dummy satinst class.
            """
            instrument_name = random_string(8)
            channel_list = channels

        self.scene = SatelliteInstrumentScene2()
        scene2 = SatelliteInstrumentScene2()

        self.scene.lon = np.ma.array(np.random.rand(3, 3),
                                     mask = np.array(np.random.rand(3, 3) * 2,
                                                     dtype = int))

        self.scene.lat = np.ma.array(np.random.rand(3, 3),
                                     mask = np.array(np.random.rand(3, 3) * 2,
                                                     dtype = int))

        self.scene[0.7] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))
        self.scene[6.4] = np.ma.array(np.random.rand(3, 3),
                                      mask = np.array(np.random.rand(3, 3) * 2,
                                                      dtype = int))

        scene2.lon = np.ma.array(np.random.rand(3, 3),
                                     mask = np.array(np.random.rand(3, 3) * 2,
                                                     dtype = int))

        scene2.lat = np.ma.array(np.random.rand(3, 3),
                                     mask = np.array(np.random.rand(3, 3) * 2,
                                                     dtype = int))

        scene2[0.7] = np.ma.array(np.random.rand(3, 3),
                                  mask = np.array(np.random.rand(3, 3) * 2,
                                                  dtype = int))
        scene2[11.5] = np.ma.array(np.random.rand(3, 3),
                                   mask = np.array(np.random.rand(3, 3) * 2,
                                                   dtype = int))

        big_scene = pp.scene.assemble_swaths([self.scene, scene2])

        data0 = big_scene[0.7].data
        data1 = self.scene[0.7].data
        data2 = scene2[0.7].data

        self.assertTrue(np.ma.allclose(data0, np.ma.concatenate((data1, data2)),
                                       rtol=EPSILON))

        data0 = big_scene[0.7].data.mask
        data1 = self.scene[0.7].data.mask
        data2 = scene2[0.7].data.mask

        self.assertTrue(np.ma.allclose(data0, np.ma.concatenate((data1, data2)),
                                       rtol=EPSILON))

        data0 = big_scene[6.4].data
        data1 = self.scene[6.4].data
        data2 = np.ma.masked_all_like(data1)

        self.assertTrue(np.ma.allclose(data0, np.ma.concatenate((data1, data2)),
                                       rtol=EPSILON))

        data0 = big_scene[6.4].data.mask
        data1 = self.scene[6.4].data.mask
        data2 = data2.mask

        self.assertTrue(np.ma.allclose(data0, np.ma.concatenate((data1, data2)),
                                       rtol=EPSILON))

        data0 = big_scene[11.5].data
        data2 = scene2[11.5].data
        data1 = np.ma.masked_all_like(data2)

        self.assertTrue(np.ma.allclose(data0, np.ma.concatenate((data1, data2)),
                                       rtol=EPSILON))

        data0 = big_scene[11.5].data.mask
        data1 = data1.mask
        data2 = scene2[11.5].data.mask

        self.assertTrue(np.ma.allclose(data0, np.ma.concatenate((data1, data2)),
                                       rtol = EPSILON))

        

    def tearDown(self):
        """Unpatch foreign modules.
        """
        unpatch_configparser()
        unpatch_projector()

if __name__ == '__main__':
    unittest.main()
