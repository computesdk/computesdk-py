"""
Binary WebSocket protocol encoder/decoder for ComputeSDK.

This module implements the binary protocol used for efficient
WebSocket communication with sandboxes. The binary protocol
provides 50-90% size reduction compared to JSON.
"""

from __future__ import annotations

import struct
from typing import Any, Dict, Union


class BinaryProtocol:
    """
    Binary WebSocket protocol encoder/decoder.

    Frame Structure:
        [1 byte: message type]
        [2 bytes: channel length (uint16, big-endian)]
        [N bytes: channel string (UTF-8)]
        [2 bytes: msg type length (uint16, big-endian)]
        [N bytes: msg type string (UTF-8)]
        [4 bytes: data length (uint32, big-endian)]
        [N bytes: data (key-value encoded)]

    Key-Value Encoding:
        [2 bytes: num_fields (uint16, big-endian)]
        For each field:
            [2 bytes: key_length (uint16)]
            [N bytes: key string (UTF-8)]
            [1 byte: value_type]
            [4 bytes: value_length (uint32, big-endian)]
            [N bytes: value data]

    Value Types:
        0x01: String (UTF-8)
        0x02: Number (float64, big-endian)
        0x03: Boolean (1 byte: 0x01 or 0x00)
        0x04: Bytes (raw bytes)
    """

    # Message type bytes
    MSG_SUBSCRIBE = 0x01
    MSG_UNSUBSCRIBE = 0x02
    MSG_DATA = 0x03
    MSG_ERROR = 0x04
    MSG_CONNECTED = 0x05

    # Value type bytes
    VAL_STRING = 0x01
    VAL_NUMBER = 0x02
    VAL_BOOLEAN = 0x03
    VAL_BYTES = 0x04

    # Message type string to byte mapping
    TYPE_TO_BYTE: Dict[str, int] = {
        "subscribe": MSG_SUBSCRIBE,
        "unsubscribe": MSG_UNSUBSCRIBE,
        "data": MSG_DATA,
        "error": MSG_ERROR,
        "connected": MSG_CONNECTED,
    }

    # Byte to message type string mapping
    BYTE_TO_TYPE: Dict[int, str] = {v: k for k, v in TYPE_TO_BYTE.items()}

    def encode(self, message: Dict[str, Any]) -> bytes:
        """
        Encode a message to binary format.

        Args:
            message: Message dict with 'type', 'channel', and 'data' keys

        Returns:
            Binary encoded message.
        """
        msg_type = message.get("type", "data")
        channel = message.get("channel", "")
        data = message.get("data", {})

        # Message type byte
        type_byte = self.TYPE_TO_BYTE.get(msg_type, self.MSG_DATA)

        # Encode channel
        channel_bytes = channel.encode("utf-8")
        channel_len = struct.pack(">H", len(channel_bytes))

        # Encode message type string
        msg_type_bytes = msg_type.encode("utf-8")
        msg_type_len = struct.pack(">H", len(msg_type_bytes))

        # Encode data as key-value pairs
        data_bytes = self._encode_data(data)
        data_len = struct.pack(">I", len(data_bytes))

        return (
            bytes([type_byte])
            + channel_len
            + channel_bytes
            + msg_type_len
            + msg_type_bytes
            + data_len
            + data_bytes
        )

    def decode(self, data: bytes) -> Dict[str, Any]:
        """
        Decode binary message to dict.

        Args:
            data: Binary encoded message

        Returns:
            Decoded message dict.
        """
        if len(data) < 1:
            return {"type": "error", "channel": "", "data": {"error": "Empty message"}}

        offset = 0

        # Read message type byte
        type_byte = data[offset]
        offset += 1

        # Read channel
        if offset + 2 > len(data):
            return {"type": "error", "channel": "", "data": {"error": "Invalid message"}}

        channel_len = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += 2

        if offset + channel_len > len(data):
            return {"type": "error", "channel": "", "data": {"error": "Invalid message"}}

        channel = data[offset : offset + channel_len].decode("utf-8")
        offset += channel_len

        # Read message type string
        if offset + 2 > len(data):
            return {"type": "error", "channel": channel, "data": {"error": "Invalid message"}}

        msg_type_len = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += 2

        if offset + msg_type_len > len(data):
            return {"type": "error", "channel": channel, "data": {"error": "Invalid message"}}

        msg_type = data[offset : offset + msg_type_len].decode("utf-8")
        offset += msg_type_len

        # Read data length
        if offset + 4 > len(data):
            return {"type": msg_type, "channel": channel, "data": {}}

        data_len = struct.unpack(">I", data[offset : offset + 4])[0]
        offset += 4

        # Read and decode data
        if offset + data_len > len(data):
            return {"type": msg_type, "channel": channel, "data": {}}

        payload = self._decode_data(data[offset : offset + data_len])

        return {
            "type": msg_type,
            "channel": channel,
            "data": payload,
        }

    def _encode_data(self, data: Dict[str, Any]) -> bytes:
        """Encode key-value data to binary format."""
        if not data:
            return struct.pack(">H", 0)

        result = struct.pack(">H", len(data))

        for key, value in data.items():
            # Encode key
            key_bytes = key.encode("utf-8")
            result += struct.pack(">H", len(key_bytes)) + key_bytes

            # Encode value based on type
            if isinstance(value, str):
                val_bytes = value.encode("utf-8")
                result += bytes([self.VAL_STRING])
                result += struct.pack(">I", len(val_bytes)) + val_bytes

            elif isinstance(value, bool):
                # Must check bool before int/float since bool is a subclass of int
                result += bytes([self.VAL_BOOLEAN])
                result += struct.pack(">I", 1)
                result += bytes([0x01 if value else 0x00])

            elif isinstance(value, (int, float)):
                result += bytes([self.VAL_NUMBER])
                result += struct.pack(">I", 8)
                result += struct.pack(">d", float(value))

            elif isinstance(value, bytes):
                result += bytes([self.VAL_BYTES])
                result += struct.pack(">I", len(value)) + value

            elif isinstance(value, dict):
                # Recursively encode nested dicts as string (JSON-like)
                import json

                val_bytes = json.dumps(value).encode("utf-8")
                result += bytes([self.VAL_STRING])
                result += struct.pack(">I", len(val_bytes)) + val_bytes

            elif isinstance(value, list):
                # Encode lists as JSON string
                import json

                val_bytes = json.dumps(value).encode("utf-8")
                result += bytes([self.VAL_STRING])
                result += struct.pack(">I", len(val_bytes)) + val_bytes

            elif value is None:
                # Encode None as empty string
                result += bytes([self.VAL_STRING])
                result += struct.pack(">I", 0)

            else:
                # Default: convert to string
                val_bytes = str(value).encode("utf-8")
                result += bytes([self.VAL_STRING])
                result += struct.pack(">I", len(val_bytes)) + val_bytes

        return result

    def _decode_data(self, data: bytes) -> Dict[str, Any]:
        """Decode binary key-value data to dict."""
        if len(data) < 2:
            return {}

        offset = 0
        num_fields = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += 2

        result: Dict[str, Any] = {}

        for _ in range(num_fields):
            if offset + 2 > len(data):
                break

            # Read key
            key_len = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2

            if offset + key_len > len(data):
                break

            key = data[offset : offset + key_len].decode("utf-8")
            offset += key_len

            if offset + 1 > len(data):
                break

            # Read value type
            val_type = data[offset]
            offset += 1

            if offset + 4 > len(data):
                break

            # Read value length
            val_len = struct.unpack(">I", data[offset : offset + 4])[0]
            offset += 4

            if offset + val_len > len(data):
                break

            # Read and decode value
            if val_type == self.VAL_STRING:
                result[key] = data[offset : offset + val_len].decode("utf-8")

            elif val_type == self.VAL_NUMBER:
                if val_len >= 8:
                    result[key] = struct.unpack(">d", data[offset : offset + 8])[0]
                else:
                    result[key] = 0.0

            elif val_type == self.VAL_BOOLEAN:
                result[key] = data[offset] == 0x01 if val_len >= 1 else False

            elif val_type == self.VAL_BYTES:
                result[key] = data[offset : offset + val_len]

            else:
                # Unknown type, try as string
                result[key] = data[offset : offset + val_len].decode("utf-8", errors="replace")

            offset += val_len

        return result


# Singleton instance for convenience
protocol = BinaryProtocol()
