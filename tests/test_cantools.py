import math
import os
import unittest
import sys
import logging
from xml.etree import ElementTree

import cantools

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class CanToolsTest(unittest.TestCase):

    maxDiff = None

    def test_vehicle(self):
        filename = os.path.join('tests', 'files', 'vehicle.dbc')
        db = cantools.db.load_file(filename)
        self.assertEqual(len(db.nodes), 1)
        self.assertEqual(db.nodes[0].name, 'Vector__XXX')
        self.assertEqual(len(db.messages), 217)
        self.assertEqual(db.messages[216].frame_id, 155872546)
        self.assertEqual(db.messages[216].nodes, ['Vector__XXX'])
        self.assertEqual(str(db.messages[0]),
                         "message('RT_SB_INS_Vel_Body_Axes', 0x9588322, False, 8, None)")
        self.assertEqual(repr(db.messages[0].signals[0]),
                         "signal('Validity_INS_Vel_Forwards', 0, 1, 'little_endian', "
                         "False, 1, 0, 0, 1, 'None', False, None, None, 'Valid when "
                         "bit is set, invalid when bit is clear.')")
        self.assertEqual(db.messages[0].signals[0].nodes, ['Vector__XXX'])
        self.assertEqual(db.messages[0].cycle_time, None)
        self.assertEqual(db.messages[0].send_type, None)
        self.assertEqual(repr(db.nodes[0]), "node('Vector__XXX', None)")
        i = 0

        for message in db.messages:
            for signal in message.signals:
                if signal.choices is not None:
                    i += 1

        self.assertEqual(i, 15)

        with open(filename, 'r') as fin:
            self.assertEqual(db.as_dbc_string(), fin.read())

    def test_motohawk(self):
        filename = os.path.join('tests', 'files', 'motohawk.dbc')

        with open(filename, 'r') as fin:
            db = cantools.db.load(fin)

        self.assertEqual(len(db.nodes), 2)
        self.assertEqual(db.nodes[0].name, 'PCM1')
        self.assertEqual(db.nodes[1].name, 'FOO')
        self.assertEqual(len(db.messages), 1)
        self.assertEqual(len(db.messages[0].signals[2].nodes), 2)
        self.assertEqual(db.messages[0].signals[2].nodes[0], 'Vector__XXX')
        self.assertEqual(db.messages[0].signals[2].nodes[1], 'FOO')
        self.assertEqual(db.messages[0].signals[1].nodes[0], 'Vector__XXX')

        with open(filename, 'r') as fin:
            self.assertEqual(db.as_dbc_string(), fin.read())

    def test_emc32(self):
        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'emc32.dbc')

        with open(filename, 'r') as fin:
            db.add_dbc(fin)

        self.assertEqual(len(db.nodes), 1)
        self.assertEqual(db.nodes[0].name, 'EMV_Statusmeldungen')
        self.assertEqual(len(db.messages), 1)
        self.assertEqual(len(db.messages[0].signals[0].nodes), 1)

    def test_foobar(self):
        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'foobar.dbc')
        db.add_dbc_file(filename)

        self.assertEqual(len(db.nodes), 2)
        self.assertEqual(db.version, '2.0')
        self.assertEqual(repr(db),
                         "version('2.0')\n"
                         "\n"
                         "node('FOO', None)\n"
                         "node('BAR', 'fam')\n"
                         "\n"
                         "message('Foo', 0x12331, True, 8, 'Foo.')\n"
                         "  signal('Bar', 1, 6, 'big_endian', False, 0.1, "
                         "0, 1.0, 5.0, 'm', False, None, None, '')\n"
                         "  signal('Foo', 7, 12, 'big_endian', True, 0.01, "
                         "250, 229.53, 270.47, 'degK', False, None, {-1: \'Foo\', "
                         "-2: \'Fie\'}, None)\n"
                         "\n"
                         "message('Fum', 0x12331, True, 8, 'Foo.')\n"
                         "  signal('Fum', 0, 12, 'little_endian', True, 1, 0, 0, 1, "
                         "'None', False, None, None, None)\n"
                         "\n"
                         "message('Bar', 0x12332, True, 8, None)\n"
                         "  signal('Binary32', 0, 32, 'little_endian', True, 1, 0, 0, "
                         "0, 'None', False, None, None, None)\n")

        message = db.lookup_message(0x12331)
        self.assertEqual(message.name, 'Fum')

    def test_padding_bit_order(self):
        """Encode and decode signals with reversed bit order.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'padding_bit_order.dbc')
        db.add_dbc_file(filename)

        # Message 0.
        msg0_frame_id = 1

        data = {
            'B': 1,      # should set byte[0]bit[7]=1
            'A': 0x2c9,  # should set byte[0]bit[1]=1 and byte[1]=c9
            'D': 0,      # should set byte[5]bit[7]=0
            'C': 0x2c9   # should set byte[4]bit[1]=1 and byte [5]=c9
        }

        encoded = db.encode_message(msg0_frame_id, data)
        self.assertEqual(encoded, b'\x82\xc9\x00\x00\x02\xc9\x00\x00')

        decoded = db.decode_message(msg0_frame_id, encoded)
        self.assertEqual(decoded, data)

        # Message 1.
        msg1_frame_id = 2

        data = {
            'E': 1,      # should set byte[0]bit[0]=1
            'F': 0x2c9,  # should set byte[0]bit[7:1]=92 and byte[1]=05
            'G': 0,      # should set byte[4]bit[0]=0
            'H': 0x2c9   # should set byte[4]bit[7:1]=92 and byte[5]=05
        }

        encoded = db.encode_message(msg1_frame_id, data)
        self.assertEqual(encoded, b'\x93\x05\x00\x00\x92\x05\x00\x00')

        decoded = db.decode_message(msg1_frame_id, encoded)
        self.assertEqual(decoded, data)

        # Message 2.
        msg2_frame_id = 3

        data = {
            'I': 1,  # should set byte[0]bit[3:0]=1
            'J': 2,  # should set byte[0]bit[7:4]=2
            'K': 3   # should set byte[1]bit[3:0]=3
        }

        encoded = db.encode_message(msg2_frame_id, data)
        self.assertEqual(encoded, b'\x21\x03\x00\x00\x00\x00\x00\x00')

        decoded = db.decode_message(msg2_frame_id, encoded)
        self.assertEqual(decoded, data)

        # Message 3.
        msg3_frame_id = 4

        data = {
            'L': 0x0123456789abcdef
        }

        encoded = db.encode_message(msg3_frame_id, data)
        self.assertTrue(encoded in [b'\x01\x23\x45\x67\x89\xab\xcd\xf0',
                                    b'\x01\x23\x45\x67\x89\xab\xcd\xef'])

        decoded = db.decode_message(msg3_frame_id, encoded)
        self.assertTrue(decoded in [data, {'L': 0x0123456789abcdef + 1}])

        # Message 4.
        msg4_frame_id = 5

        data = {
            'M': 0x0123456789abcdef
        }

        encoded = db.encode_message(msg4_frame_id, data)
        self.assertTrue(encoded in [b'\xf0\xcd\xab\x89\x67\x45\x23\x01',
                                    b'\xef\xcd\xab\x89\x67\x45\x23\x01'])

        decoded = db.decode_message(msg4_frame_id, encoded)
        self.assertTrue(decoded in [data, {'M': 0x0123456789abcdef + 1}])

    def test_motohawk_encode_decode(self):
        """Encode and decode the signals in a ExampleMessage frame.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'motohawk.dbc')
        db.add_dbc_file(filename)

        example_message_frame_id = 496

        # Encode with non-enumerated values.
        data = {
            'Temperature': 250.55,
            'AverageRadius': 3.2,
            'Enable': 1
        }

        encoded = db.encode_message(example_message_frame_id, data)
        self.assertEqual(encoded, b'\xc0\x06\xe0\x00\x00\x00\x00\x00')

        # Encode with enumerated values.
        data = {
            'Temperature': 250.55,
            'AverageRadius': 3.2,
            'Enable': 'Enabled'
        }

        encoded = db.encode_message(example_message_frame_id, data)
        self.assertEqual(encoded, b'\xc0\x06\xe0\x00\x00\x00\x00\x00')

        decoded = db.decode_message(example_message_frame_id, encoded)
        self.assertEqual(decoded, data)

    def test_big_endian_no_decode_choices(self):
        """Decode a big endian signal with `decode_choices` set to False.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'motohawk.dbc')
        db.add_dbc_file(filename)

        data = {
            'Temperature': 250.55,
            'AverageRadius': 3.2,
            'Enable': 1
        }

        decoded = db.decode_message(496,
                                    b'\xc0\x06\xe0\x00\x00\x00\x00\x00',
                                    decode_choices=False)
        self.assertEqual(decoded, data)

    def test_little_endian_no_decode_choices(self):
        """Decode a little endian signal with `decode_choices` set to False.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'socialledge.dbc')
        db.add_dbc_file(filename)

        data = {
            'DRIVER_HEARTBEAT_cmd': 1
        }

        decoded = db.decode_message(100,
                                    b'\x01\x00\x00\x00\x00\x00\x00\x00',
                                    decode_choices=False)
        self.assertEqual(decoded, data)

        data = {
            'DRIVER_HEARTBEAT_cmd': 'DRIVER_HEARTBEAT_cmd_SYNC'
        }

        decoded = db.decode_message(100,
                                    b'\x01\x00\x00\x00\x00\x00\x00\x00')
        self.assertEqual(decoded, data)

    def test_encode_decode_no_scaling(self):
        """Encode and decode a message without scaling the signal values.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'motohawk.dbc')
        db.add_dbc_file(filename)

        data = {
            'Temperature': 55,
            'AverageRadius': 32,
            'Enable': 'Enabled'
        }

        encoded = db.encode_message(496,
                                    data,
                                    scaling=False)
        self.assertEqual(encoded, b'\xc0\x06\xe0\x00\x00\x00\x00\x00')

        decoded = db.decode_message(496,
                                    encoded,
                                    scaling=False)
        self.assertEqual(decoded, data)

    def test_encode_decode_no_scaling_no_decode_choices(self):
        """Encode and decode a message without scaling the signal values, not
        decoding choices.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'motohawk.dbc')
        db.add_dbc_file(filename)

        data = {
            'Temperature': 3,
            'AverageRadius': 2,
            'Enable': 1
        }

        encoded = db.encode_message(496,
                                    data,
                                    scaling=False)
        self.assertEqual(encoded, b'\x84\x00\x60\x00\x00\x00\x00\x00')

        decoded = db.decode_message(496,
                                    encoded,
                                    decode_choices=False,
                                    scaling=False)
        self.assertEqual(decoded, data)

    def test_socialledge(self):
        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'socialledge.dbc')
        db.add_dbc_file(filename)

        # Verify nodes.
        self.assertEqual(len(db.nodes), 5)
        self.assertEqual(db.nodes[0].name, 'DBG')
        self.assertEqual(db.nodes[0].comment, None)
        self.assertEqual(db.nodes[1].name, 'DRIVER')
        self.assertEqual(db.nodes[1].comment,
                         'The driver controller driving the car')
        self.assertEqual(db.nodes[2].name, 'IO')
        self.assertEqual(db.nodes[2].comment, None)
        self.assertEqual(db.nodes[3].name, 'MOTOR')
        self.assertEqual(db.nodes[3].comment,
                         'The motor controller of the car')
        self.assertEqual(db.nodes[4].name, 'SENSOR')
        self.assertEqual(db.nodes[4].comment,
                         'The sensor controller of the car')

        # Verify messages and their signals.
        self.assertEqual(len(db.messages), 5)
        self.assertEqual(db.messages[0].name, 'DRIVER_HEARTBEAT')
        self.assertEqual(db.messages[0].comment,
                         'Sync message used to synchronize the controllers')
        self.assertEqual(db.messages[0].signals[0].choices[0],
                         'DRIVER_HEARTBEAT_cmd_NOOP')
        self.assertEqual(db.messages[0].signals[0].choices[1],
                         'DRIVER_HEARTBEAT_cmd_SYNC')
        self.assertEqual(db.messages[0].signals[0].choices[2],
                         'DRIVER_HEARTBEAT_cmd_REBOOT')
        self.assertEqual(db.messages[1].name, 'IO_DEBUG')
        self.assertEqual(db.messages[2].name, 'MOTOR_CMD')
        self.assertEqual(db.messages[3].name, 'MOTOR_STATUS')
        self.assertEqual(db.messages[4].name, 'SENSOR_SONARS')

        sensor_sonars = db.messages[-1]

        self.assertFalse(db.messages[0].is_multiplexed())
        self.assertTrue(sensor_sonars.is_multiplexed())
        self.assertEqual(sensor_sonars.signals[-1].name, 'SENSOR_SONARS_no_filt_rear')
        self.assertEqual(sensor_sonars.signals[-1].multiplexer_id, 1)
        self.assertEqual(sensor_sonars.signals[2].name, 'SENSOR_SONARS_left')
        self.assertEqual(sensor_sonars.signals[2].multiplexer_id, 0)
        self.assertEqual(sensor_sonars.signals[0].name, 'SENSOR_SONARS_mux')
        self.assertEqual(sensor_sonars.signals[0].is_multiplexer, True)

        self.assertEqual(sensor_sonars.get_multiplexer_signal_name(),
                         'SENSOR_SONARS_mux')
        signals = sensor_sonars.get_signals_by_multiplexer_id(0)
        self.assertEqual(len(signals), 6)
        self.assertEqual(signals[-1].name, 'SENSOR_SONARS_rear')

        self.assertEqual(db.version, '')

    def test_socialledge_encode_decode_mux_0(self):
        """Encode and decode the signals in a SENSOR_SONARS frame with mux 0.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'socialledge.dbc')
        db.add_dbc_file(filename)

        frame_id = 200
        data = {
            'SENSOR_SONARS_mux': 0,
            'SENSOR_SONARS_err_count': 1,
            'SENSOR_SONARS_left': 2,
            'SENSOR_SONARS_middle': 3,
            'SENSOR_SONARS_right': 4,
            'SENSOR_SONARS_rear': 5
        }

        encoded = db.encode_message(frame_id, data)
        self.assertEqual(encoded, b'\x10\x00\x14\xe0\x01( \x03')

        decoded = db.decode_message(frame_id, encoded)
        self.assertEqual(decoded, data)

    def test_socialledge_encode_decode_mux_1(self):
        """Encode and decode the signals in a SENSOR_SONARS frame with mux 1.

        """

        db = cantools.db.File()
        filename = os.path.join('tests', 'files', 'socialledge.dbc')
        db.add_dbc_file(filename)

        frame_id = 200
        data = {
            'SENSOR_SONARS_mux': 1,
            'SENSOR_SONARS_err_count': 2,
            'SENSOR_SONARS_no_filt_left': 3,
            'SENSOR_SONARS_no_filt_middle': 4,
            'SENSOR_SONARS_no_filt_right': 5,
            'SENSOR_SONARS_no_filt_rear': 6
        }

        encoded = db.encode_message(frame_id, data)
        self.assertEqual(encoded, b'!\x00\x1e\x80\x022\xc0\x03')

        decoded = db.decode_message(frame_id, encoded)
        self.assertEqual(decoded, data)

    def test_add_message(self):
        db = cantools.db.File()
        signals = [cantools.db.Signal(name='signal',
                                      start=0,
                                      length=4,
                                      nodes=['foo'],
                                      byte_order='big_endian',
                                      is_signed=False,
                                      scale=1.0,
                                      offset=10,
                                      minimum=10.0,
                                      maximum=100.0,
                                      unit='m/s',
                                      choices=None,
                                      comment=None)]
        message = cantools.db.Message(frame_id=37,
                                      name='message',
                                      length=8,
                                      nodes=['bar'],
                                      signals=signals,
                                      comment='')
        db.add_message(message)
        self.assertEqual(len(db.messages), 1)

    def test_command_line_decode(self):
        argv = ['cantools', 'decode', 'tests/files/socialledge.dbc']
        input_data = """  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00
  vcan0  064   [8]  F0 01 FF FF FF FF FF FF
"""
        expected_output = """  vcan0  0C8   [8]  F0 00 00 00 00 00 00 00 :: SENSOR_SONARS(SENSOR_SONARS_mux: 0, SENSOR_SONARS_err_count: 15, SENSOR_SONARS_left: 0.0, SENSOR_SONARS_middle: 0.0, SENSOR_SONARS_right: 0.0, SENSOR_SONARS_rear: 0.0)
  vcan0  064   [8]  F0 01 FF FF FF FF FF FF :: DRIVER_HEARTBEAT(DRIVER_HEARTBEAT_cmd: 240)
"""

        stdin = sys.stdin
        stdout = sys.stdout
        sys.argv = argv
        sys.stdin = StringIO(input_data)
        sys.stdout = StringIO()

        try:
            cantools._main()

        finally:
            actual_output = sys.stdout.getvalue()
            sys.stdin = stdin
            sys.stdout = stdout

        self.assertEqual(actual_output, expected_output)

    def test_the_homer(self):
        filename = os.path.join('tests', 'files', 'the_homer.kcd')
        db = cantools.db.load_file(filename)

        self.assertEqual(db.version, '1.23')
        self.assertEqual(len(db.nodes), 18)
        self.assertEqual(db.nodes[0].name, 'Motor ACME')
        self.assertEqual(db.nodes[1].name, 'Motor alternative supplier')
        self.assertEqual(len(db.buses), 3)
        self.assertEqual(db.buses[0].name, 'Motor')
        self.assertEqual(db.buses[1].name, 'Instrumentation')
        self.assertEqual(db.buses[2].name, 'Comfort')
        self.assertEqual(db.buses[0].comment, None)
        self.assertEqual(db.buses[0].baudrate, 500000)
        self.assertEqual(db.buses[1].baudrate, 125000)

        self.assertEqual(len(db.messages), 27)
        self.assertEqual(db.messages[0].frame_id, 0xa)
        self.assertEqual(db.messages[0].is_extended_frame, False)
        self.assertEqual(db.messages[0].name, 'Airbag')
        self.assertEqual(db.messages[0].length, 3)
        self.assertEqual(len(db.messages[0].signals), 8)
        self.assertEqual(db.messages[0].comment, None)
        self.assertEqual(db.messages[0].send_type, None)
        self.assertEqual(db.messages[0].cycle_time, 0)
        self.assertEqual(db.messages[0].bus_name, 'Motor')

        self.assertEqual(db.messages[1].frame_id, 0x0B2)
        self.assertEqual(db.messages[1].name, 'ABS')
        self.assertEqual(db.messages[1].cycle_time, 100)

        self.assertEqual(db.messages[3].frame_id, 0x400)
        self.assertEqual(db.messages[3].name, 'Emission')
        self.assertEqual(db.messages[3].length, 5)

        self.assertEqual(db.messages[-1].bus_name, 'Comfort')

        seat_configuration = db.messages[0].signals[-1]

        self.assertEqual(seat_configuration.name, 'SeatConfiguration')
        self.assertEqual(seat_configuration.start, 16)
        self.assertEqual(seat_configuration.length, 8)
        self.assertEqual(seat_configuration.nodes, [])
        self.assertEqual(seat_configuration.byte_order, 'little_endian')
        self.assertEqual(seat_configuration.is_signed, False)
        self.assertEqual(seat_configuration.is_float, False)
        self.assertEqual(seat_configuration.scale, 1)
        self.assertEqual(seat_configuration.offset, 0)
        self.assertEqual(seat_configuration.minimum, None)
        self.assertEqual(seat_configuration.maximum, None)
        self.assertEqual(seat_configuration.unit, None)
        self.assertEqual(seat_configuration.choices, None)
        self.assertEqual(seat_configuration.comment, None)

        tank_temperature = db.messages[10].signals[1]

        self.assertEqual(tank_temperature.name, 'TankTemperature')
        self.assertEqual(tank_temperature.start, 16)
        self.assertEqual(tank_temperature.length, 16)
        self.assertEqual(tank_temperature.nodes, [])
        self.assertEqual(tank_temperature.byte_order, 'little_endian')
        self.assertEqual(tank_temperature.is_signed, True)
        self.assertEqual(tank_temperature.is_float, False)
        self.assertEqual(tank_temperature.scale, 1)
        self.assertEqual(tank_temperature.offset, 0)
        self.assertEqual(tank_temperature.minimum, None)
        self.assertEqual(tank_temperature.maximum, None)
        self.assertEqual(tank_temperature.unit, 'Cel')
        self.assertEqual(tank_temperature.choices, None)
        self.assertEqual(tank_temperature.comment, None)

        speed_km = db.messages[1].signals[1]

        self.assertEqual(speed_km.name, 'SpeedKm')
        self.assertEqual(speed_km.start, 30)
        self.assertEqual(speed_km.length, 24)
        self.assertEqual(speed_km.nodes, [])
        self.assertEqual(speed_km.byte_order, 'little_endian')
        self.assertEqual(speed_km.is_signed, False)
        self.assertEqual(speed_km.is_float, False)
        self.assertEqual(speed_km.scale, 0.2)
        self.assertEqual(speed_km.offset, 0)
        self.assertEqual(speed_km.minimum, None)
        self.assertEqual(speed_km.maximum, None)
        self.assertEqual(speed_km.unit, 'km/h')
        self.assertEqual(speed_km.choices, None)
        self.assertEqual(speed_km.comment,
                         'Middle speed of front wheels in kilometers per hour.')

        outside_temp = db.messages[1].signals[0]

        self.assertEqual(outside_temp.name, 'OutsideTemp')
        self.assertEqual(outside_temp.start, 18)
        self.assertEqual(outside_temp.length, 12)
        self.assertEqual(outside_temp.nodes, [])
        self.assertEqual(outside_temp.byte_order, 'big_endian')
        self.assertEqual(outside_temp.is_signed, False)
        self.assertEqual(outside_temp.is_float, False)
        self.assertEqual(outside_temp.scale, 0.05)
        self.assertEqual(outside_temp.offset, -40)
        self.assertEqual(outside_temp.minimum, 0)
        self.assertEqual(outside_temp.maximum, 100)
        self.assertEqual(outside_temp.unit, 'Cel')
        self.assertEqual(outside_temp.choices, None)
        self.assertEqual(outside_temp.comment, 'Outside temperature.')

        ambient_lux = db.messages[24].signals[0]

        self.assertEqual(ambient_lux.name, 'AmbientLux')
        self.assertEqual(ambient_lux.start, 0)
        self.assertEqual(ambient_lux.length, 64)
        self.assertEqual(ambient_lux.nodes, [])
        self.assertEqual(ambient_lux.byte_order, 'little_endian')
        self.assertEqual(ambient_lux.is_signed, False)
        self.assertEqual(ambient_lux.is_float, True)
        self.assertEqual(ambient_lux.scale, 1)
        self.assertEqual(ambient_lux.offset, 0)
        self.assertEqual(ambient_lux.minimum, None)
        self.assertEqual(ambient_lux.maximum, None)
        self.assertEqual(ambient_lux.unit, 'Lux')
        self.assertEqual(ambient_lux.choices, None)
        self.assertEqual(ambient_lux.comment, None)

        windshield_humidity = db.messages[25].signals[0]

        self.assertEqual(windshield_humidity.name, 'Windshield')
        self.assertEqual(windshield_humidity.start, 0)
        self.assertEqual(windshield_humidity.length, 32)
        self.assertEqual(windshield_humidity.nodes, [])
        self.assertEqual(windshield_humidity.byte_order, 'little_endian')
        self.assertEqual(windshield_humidity.is_signed, False)
        self.assertEqual(windshield_humidity.is_float, True)
        self.assertEqual(windshield_humidity.scale, 1)
        self.assertEqual(windshield_humidity.offset, 0)
        self.assertEqual(windshield_humidity.minimum, None)
        self.assertEqual(windshield_humidity.maximum, None)
        self.assertEqual(windshield_humidity.unit, '% RH')
        self.assertEqual(windshield_humidity.choices, None)
        self.assertEqual(windshield_humidity.comment, None)

    def test_the_homer_encode_length(self):
        filename = os.path.join('tests', 'files', 'the_homer.kcd')
        db = cantools.db.File()
        db.add_kcd_file(filename)

        frame_id = 0x400
        data = {
            'MIL': 0,
            'Enginespeed': 127,
            'NoxSensor': 127,
        }

        encoded = db.encode_message(frame_id, data)
        self.assertEqual(len(encoded), 5)
        self.assertEqual(encoded, b'\xfe\x00\xfe\x00\x00')

    def test_the_homer_float(self):
        filename = os.path.join('tests', 'files', 'the_homer.kcd')
        db = cantools.db.File()
        db.add_kcd_file(filename)

        frame_id = 0x832
        encoded = db.encode_message(frame_id, {'AmbientLux': math.pi})
        self.assertEqual(len(encoded), 8)
        self.assertEqual(encoded, b'\x18\x2d\x44\x54\xfb\x21\x09\x40')
        decoded = db.decode_message(frame_id, b'\x18\x2d\x44\x54\xfb\x21\x09\x40')
        self.assertEqual(decoded['AmbientLux'], math.pi)

        frame_id = 0x845
        encoded = db.encode_message(frame_id, {'Windshield': math.pi})
        self.assertEqual(len(encoded), 4)
        self.assertEqual(encoded, b'\xdb\x0f\x49\x40')
        decoded = db.decode_message(frame_id, b'\xdb\x0f\x49\x40')
        self.assertEqual(decoded['Windshield'], 3.1415927410125732)

    def test_jopp_5_0_sym(self):
        filename = os.path.join('tests', 'files', 'jopp-5.0.sym')
        db = cantools.db.File()

        with self.assertRaises(ValueError) as cm:
            db.add_sym_file(filename)

        self.assertEqual(str(cm.exception), 'Only SYM version 6.0 is supported.')

    def test_jopp_6_0_sym(self):
        filename = os.path.join('tests', 'files', 'jopp-6.0.sym')
        db = cantools.db.File()
        db.add_sym_file(filename)

        self.assertEqual(len(db.messages), 6)
        self.assertEqual(len(db.messages[0].signals), 0)

        # Message1.
        message_1 = db.messages[3]
        self.assertEqual(len(message_1.signals), 2)
        self.assertEqual(message_1.frame_id, 0)
        self.assertEqual(message_1.is_extended_frame, False)
        self.assertEqual(message_1.name, 'Message1')
        self.assertEqual(message_1.length, 8)
        self.assertEqual(message_1.nodes, [])
        self.assertEqual(message_1.send_type, None)
        self.assertEqual(message_1.cycle_time, 30)
        self.assertEqual(len(message_1.signals), 2)
        self.assertEqual(message_1.comment, None)
        self.assertEqual(message_1.bus_name, None)

        signal_1 = message_1.signals[0]
        self.assertEqual(signal_1.name, 'Signal1')
        self.assertEqual(signal_1.start, 0)
        self.assertEqual(signal_1.length, 11)
        self.assertEqual(signal_1.nodes, [])
        self.assertEqual(signal_1.byte_order, 'big_endian')
        self.assertEqual(signal_1.is_signed, False)
        self.assertEqual(signal_1.scale, 1)
        self.assertEqual(signal_1.offset, 0)
        self.assertEqual(signal_1.minimum, None)
        self.assertEqual(signal_1.maximum, 255)
        self.assertEqual(signal_1.unit, 'A')
        self.assertEqual(signal_1.choices, None)
        self.assertEqual(signal_1.comment, None)
        self.assertEqual(signal_1.is_multiplexer, False)
        self.assertEqual(signal_1.multiplexer_id, None)
        self.assertEqual(signal_1.is_float, False)

        signal_2 = message_1.signals[1]
        self.assertEqual(signal_2.name, 'Signal2')
        self.assertEqual(signal_2.start, 32)
        self.assertEqual(signal_2.length, 32)
        self.assertEqual(signal_2.nodes, [])
        self.assertEqual(signal_2.byte_order, 'big_endian')
        self.assertEqual(signal_2.is_signed, False)
        self.assertEqual(signal_2.scale, 1)
        self.assertEqual(signal_2.offset, 48)
        self.assertEqual(signal_2.minimum, 16)
        self.assertEqual(signal_2.maximum, 130)
        self.assertEqual(signal_2.unit, 'V')
        self.assertEqual(signal_2.choices, None)
        self.assertEqual(signal_2.comment, None)
        self.assertEqual(signal_2.is_multiplexer, False)
        self.assertEqual(signal_2.multiplexer_id, None)
        self.assertEqual(signal_2.is_float, True)

        # Message2.
        message_2 = db.messages[1]
        self.assertEqual(message_2.frame_id, 0x22)
        self.assertEqual(message_2.is_extended_frame, True)
        self.assertEqual(message_2.name, 'Message2')
        self.assertEqual(message_2.length, 8)
        self.assertEqual(message_2.nodes, [])
        self.assertEqual(message_2.send_type, None)
        self.assertEqual(message_2.cycle_time, None)
        self.assertEqual(len(message_2.signals), 1)
        self.assertEqual(message_2.comment, None)
        self.assertEqual(message_2.bus_name, None)
        self.assertEqual(message_2.is_multiplexed(), False)

        signal_3 = message_2.signals[0]
        self.assertEqual(signal_3.name, 'Signal3')
        self.assertEqual(signal_3.start, 2)
        self.assertEqual(signal_3.length, 11)
        self.assertEqual(signal_3.nodes, [])
        self.assertEqual(signal_3.byte_order, 'little_endian')
        self.assertEqual(signal_3.is_signed, True)
        self.assertEqual(signal_3.scale, 1)
        self.assertEqual(signal_3.offset, 0)
        self.assertEqual(signal_3.minimum, 0)
        self.assertEqual(signal_3.maximum, 1)
        self.assertEqual(signal_3.unit, None)
        self.assertEqual(signal_3.choices, {0: 'foo', 1: 'bar'})
        self.assertEqual(signal_3.comment, None)
        self.assertEqual(signal_3.is_multiplexer, False)
        self.assertEqual(signal_3.multiplexer_id, None)
        self.assertEqual(signal_3.is_float, False)

        # Symbol2.
        signal_4 = db.messages[4].signals[0]
        self.assertEqual(signal_4.name, 'Signal4')
        self.assertEqual(signal_4.start, 0)
        self.assertEqual(signal_4.length, 64)
        self.assertEqual(signal_4.nodes, [])
        self.assertEqual(signal_4.byte_order, 'big_endian')
        self.assertEqual(signal_4.is_signed, False)
        self.assertEqual(signal_4.scale, 6)
        self.assertEqual(signal_4.offset, 5)
        self.assertEqual(signal_4.minimum, -1.7e+308)
        self.assertEqual(signal_4.maximum, 1.7e+308)
        self.assertEqual(signal_4.unit, '*UU')
        self.assertEqual(signal_4.choices, None)
        self.assertEqual(signal_4.comment, None)
        self.assertEqual(signal_4.is_multiplexer, False)
        self.assertEqual(signal_4.multiplexer_id, None)
        self.assertEqual(signal_4.is_float, True)

        # Symbol3.
        symbol_3 = db.messages[5]
        self.assertEqual(symbol_3.frame_id, 0x33)
        self.assertEqual(symbol_3.length, 8)
        self.assertTrue(symbol_3.is_multiplexed())
        self.assertEqual(len(symbol_3.signals), 4)
        multiplexer = symbol_3.signals[0]
        self.assertEqual(multiplexer.name, 'Multiplexer1')
        self.assertEqual(multiplexer.start, 0)
        self.assertEqual(multiplexer.length, 3)
        self.assertEqual(multiplexer.is_multiplexer, True)
        self.assertEqual(multiplexer.multiplexer_id, None)
        signal_1 = symbol_3.signals[1]
        self.assertEqual(signal_1.name, 'Signal1')
        self.assertEqual(signal_1.start, 3)
        self.assertEqual(signal_1.length, 11)
        self.assertEqual(signal_1.is_multiplexer, False)
        self.assertEqual(signal_1.multiplexer_id, 0)
        signal_2 = symbol_3.signals[2]
        self.assertEqual(signal_2.name, 'Signal2')
        self.assertEqual(signal_2.start, 6)
        self.assertEqual(signal_2.length, 32)
        self.assertEqual(signal_2.is_multiplexer, False)
        self.assertEqual(signal_2.multiplexer_id, 1)
        signal_3 = symbol_3.signals[3]
        self.assertEqual(signal_3.name, 'Signal3')
        self.assertEqual(signal_3.start, 9)
        self.assertEqual(signal_3.length, 11)
        self.assertEqual(signal_3.is_multiplexer, False)
        self.assertEqual(signal_3.multiplexer_id, 2)

        # Encode and decode.
        frame_id = 0x009
        encoded = db.encode_message(frame_id, {})
        self.assertEqual(len(encoded), 8)
        self.assertEqual(encoded, 8 * b'\x00')
        decoded = db.decode_message(frame_id, encoded)
        self.assertEqual(decoded, {})

        frame_id = 0x022
        encoded = db.encode_message(frame_id, {'Signal3': 'bar'})
        self.assertEqual(len(encoded), 8)
        self.assertEqual(encoded, b'\x04\x00\x00\x00\x00\x00\x00\x00')
        decoded = db.decode_message(frame_id, encoded)
        self.assertEqual(decoded['Signal3'], 'bar')

    def test_load_bad_format(self):
        with self.assertRaises(cantools.db.UnsupportedDatabaseFormatError):
            cantools.db.load(StringIO(''))

    def test_add_bad_kcd_string(self):
        db = cantools.db.File()

        with self.assertRaises(ElementTree.ParseError) as cm:
            db.add_kcd_string('not xml')

        self.assertEqual(str(cm.exception), 'syntax error: line 1, column 0')

    def test_bus(self):
        bus = cantools.db.bus.Bus('foo')
        self.assertEqual(repr(bus), "bus('foo', None)")

        bus = cantools.db.bus.Bus('foo', 'bar')
        self.assertEqual(repr(bus), "bus('foo', 'bar')")

    def test_num(self):
        self.assertEqual(cantools.db.formats.utils.num('1'), 1)
        self.assertEqual(cantools.db.formats.utils.num('1.0'), 1.0)

        with self.assertRaises(ValueError):
            cantools.db.formats.utils.num('x')

    def test_timing(self):
        filename = os.path.join('tests', 'files', 'timing.dbc')
        db = cantools.db.load_file(filename)

        # Message cycle time is 200, as given by BA_.
        message = db.lookup_message(1)
        self.assertEqual(message.cycle_time, 200)
        self.assertEqual(message.send_type, 'cyclic')

        # Default message cycle time is 0, as given by BA_DEF_DEF_.
        message = db.lookup_message(2)
        self.assertEqual(message.cycle_time, 0)
        self.assertEqual(message.send_type, 'none')

        with open(filename, 'r') as fin:
            self.assertEqual(db.as_dbc_string(), fin.read())


# This file is not '__main__' when executed via 'python setup.py
# test'.
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    unittest.main()
