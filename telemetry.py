"""
telemetry_converter.py
Converts two different JSON telemetry formats into a single unified format.
"""

import unittest
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Format 1 Converter
# ---------------------------------------------------------------------------

def convertFromFormat1(jsonObject: dict) -> dict:
    """
    Convert Format 1 telemetry into the unified output format.

    Field mappings:
        deviceID        -> deviceID
        deviceType      -> deviceType
        timestamp       -> timestamp  (already in milliseconds, kept as-is)
        location        -> location   (string split by "/" into structured dict)
        operationStatus -> data.status
        temp            -> data.temperature
    """
    # Split location string "country/city/area/factory/section" into parts
    location_parts = jsonObject["location"].split("/")
    location = {
        "country": location_parts[0],
        "city":    location_parts[1],
        "area":    location_parts[2],
        "factory": location_parts[3],
        "section": location_parts[4],
    }

    return {
        "deviceID":   jsonObject["deviceID"],
        "deviceType": jsonObject["deviceType"],
        "timestamp":  jsonObject["timestamp"],   # already epoch milliseconds
        "location":   location,
        "data": {
            "status":      jsonObject["operationStatus"],  # operationStatus -> status
            "temperature": jsonObject["temp"],             # temp -> temperature
        },
    }


# ---------------------------------------------------------------------------
# Format 2 Converter
# ---------------------------------------------------------------------------

def convertFromFormat2(jsonObject: dict) -> dict:
    """
    Convert Format 2 telemetry into the unified output format.

    Field mappings:
        device.id   -> deviceID
        device.type -> deviceType
        timestamp   -> timestamp  (ISO 8601 string converted to epoch milliseconds)
        country / city / area / factory / section -> location dict
        data.status / data.temperature            -> data dict (kept as-is)
    """
    # --- Timestamp conversion: ISO 8601 → epoch milliseconds ---------------
    # datetime.fromisoformat() does not accept the trailing "Z" in Python < 3.11,
    # so we replace "Z" with "+00:00" to produce a valid offset-aware string.
    iso_str = jsonObject["timestamp"].replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso_str)                       # offset-aware datetime
    # Convert to UTC epoch seconds, then multiply by 1000 for milliseconds
    timestamp_ms = int(dt.timestamp() * 1000)

    # --- Location: fields are already flat in Format 2 ---------------------
    location = {
        "country": jsonObject["country"],
        "city":    jsonObject["city"],
        "area":    jsonObject["area"],
        "factory": jsonObject["factory"],
        "section": jsonObject["section"],
    }

    return {
        "deviceID":   jsonObject["device"]["id"],    # nested device.id   -> deviceID
        "deviceType": jsonObject["device"]["type"],  # nested device.type -> deviceType
        "timestamp":  timestamp_ms,
        "location":   location,
        "data":       jsonObject["data"],            # data block kept as-is
    }


# ---------------------------------------------------------------------------
# Format Detection & Main Entry Point
# ---------------------------------------------------------------------------

def detectAndConvert(jsonObject: dict) -> dict:
    """
    Auto-detect the telemetry format and call the appropriate converter.

    Detection logic:
        - Format 1 has a top-level "deviceID" key (flat structure).
        - Format 2 has a nested "device" key (nested structure).
    """
    if "deviceID" in jsonObject:
        return convertFromFormat1(jsonObject)
    elif "device" in jsonObject:
        return convertFromFormat2(jsonObject)
    else:
        raise ValueError("Unknown telemetry format: cannot find 'deviceID' or 'device' key.")


def main():
    import json

    # --- Sample Format 1 payload -------------------------------------------
    format1 = {
        "deviceID": "dh28dslkja",
        "deviceType": "LaserCutter",
        "timestamp": 1624445837783,
        "location": "japan/tokyo/keiyō-industrial-zone/daikibo-factory-meiyo/section-1",
        "operationStatus": "healthy",
        "temp": 22,
    }

    # --- Sample Format 2 payload -------------------------------------------
    format2 = {
        "device": {"id": "dh28dslkja", "type": "LaserCutter"},
        "timestamp": "2021-06-23T10:57:17.783Z",
        "country": "japan",
        "city": "tokyo",
        "area": "keiyō-industrial-zone",
        "factory": "daikibo-factory-meiyo",
        "section": "section-1",
        "data": {"status": "healthy", "temperature": 22},
    }

    print("=== Format 1 → Unified ===")
    print(json.dumps(detectAndConvert(format1), indent=2, ensure_ascii=False))

    print("\n=== Format 2 → Unified ===")
    print(json.dumps(detectAndConvert(format2), indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

EXPECTED_OUTPUT = {
    "deviceID": "dh28dslkja",
    "deviceType": "LaserCutter",
    "timestamp": 1624445837783,
    "location": {
        "country": "japan",
        "city": "tokyo",
        "area": "keiyō-industrial-zone",
        "factory": "daikibo-factory-meiyo",
        "section": "section-1",
    },
    "data": {
        "status": "healthy",
        "temperature": 22,
    },
}


class TestTelemetryConverter(unittest.TestCase):

    FORMAT1 = {
        "deviceID": "dh28dslkja",
        "deviceType": "LaserCutter",
        "timestamp": 1624445837783,
        "location": "japan/tokyo/keiyō-industrial-zone/daikibo-factory-meiyo/section-1",
        "operationStatus": "healthy",
        "temp": 22,
    }

    FORMAT2 = {
        "device": {"id": "dh28dslkja", "type": "LaserCutter"},
        "timestamp": "2021-06-23T10:57:17.783Z",
        "country": "japan",
        "city": "tokyo",
        "area": "keiyō-industrial-zone",
        "factory": "daikibo-factory-meiyo",
        "section": "section-1",
        "data": {"status": "healthy", "temperature": 22},
    }

    # --- Format 1 tests ----------------------------------------------------

    def test_format1_full_output(self):
        """Entire output of convertFromFormat1 must match expected."""
        self.assertEqual(convertFromFormat1(self.FORMAT1), EXPECTED_OUTPUT)

    def test_format1_device_fields(self):
        result = convertFromFormat1(self.FORMAT1)
        self.assertEqual(result["deviceID"], "dh28dslkja")
        self.assertEqual(result["deviceType"], "LaserCutter")

    def test_format1_timestamp_unchanged(self):
        """Format 1 timestamp is already epoch ms and must not be altered."""
        result = convertFromFormat1(self.FORMAT1)
        self.assertEqual(result["timestamp"], 1624445837783)

    def test_format1_location_split(self):
        """Location string must be split into a structured dict."""
        result = convertFromFormat1(self.FORMAT1)
        self.assertEqual(result["location"]["country"], "japan")
        self.assertEqual(result["location"]["city"], "tokyo")
        self.assertEqual(result["location"]["area"], "keiyō-industrial-zone")
        self.assertEqual(result["location"]["factory"], "daikibo-factory-meiyo")
        self.assertEqual(result["location"]["section"], "section-1")

    def test_format1_data_mapping(self):
        """operationStatus → data.status and temp → data.temperature."""
        result = convertFromFormat1(self.FORMAT1)
        self.assertEqual(result["data"]["status"], "healthy")
        self.assertEqual(result["data"]["temperature"], 22)

    def test_format1_no_extra_keys(self):
        """Output must not contain legacy keys operationStatus or temp."""
        result = convertFromFormat1(self.FORMAT1)
        self.assertNotIn("operationStatus", result)
        self.assertNotIn("temp", result)

    # --- Format 2 tests ----------------------------------------------------

    def test_format2_full_output(self):
        """Entire output of convertFromFormat2 must match expected."""
        self.assertEqual(convertFromFormat2(self.FORMAT2), EXPECTED_OUTPUT)

    def test_format2_device_extraction(self):
        """Nested device.id / device.type must be promoted to top level."""
        result = convertFromFormat2(self.FORMAT2)
        self.assertEqual(result["deviceID"], "dh28dslkja")
        self.assertEqual(result["deviceType"], "LaserCutter")

    def test_format2_timestamp_conversion(self):
        """ISO 8601 timestamp must be converted to epoch milliseconds."""
        result = convertFromFormat2(self.FORMAT2)
        self.assertEqual(result["timestamp"], 1624445837783)

    def test_format2_location_structure(self):
        result = convertFromFormat2(self.FORMAT2)
        self.assertEqual(result["location"]["country"], "japan")
        self.assertEqual(result["location"]["city"], "tokyo")
        self.assertEqual(result["location"]["section"], "section-1")

    def test_format2_data_passthrough(self):
        """data block must be passed through unchanged."""
        result = convertFromFormat2(self.FORMAT2)
        self.assertEqual(result["data"]["status"], "healthy")
        self.assertEqual(result["data"]["temperature"], 22)

    def test_format2_no_extra_keys(self):
        """Output must not contain flat location keys from Format 2."""
        result = convertFromFormat2(self.FORMAT2)
        for key in ("country", "city", "area", "factory", "section", "device"):
            self.assertNotIn(key, result)

    # --- Auto-detection tests ----------------------------------------------

    def test_detect_format1(self):
        self.assertEqual(detectAndConvert(self.FORMAT1), EXPECTED_OUTPUT)

    def test_detect_format2(self):
        self.assertEqual(detectAndConvert(self.FORMAT2), EXPECTED_OUTPUT)

    def test_detect_unknown_raises(self):
        with self.assertRaises(ValueError):
            detectAndConvert({"foo": "bar"})


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Run main demo, then execute unit tests
    main()
    print("\n=== Running Unit Tests ===\n")
    unittest.main(argv=[""], verbosity=2, exit=False)