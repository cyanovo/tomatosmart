import json
from unittest.mock import patch

from yuxi.iot.schemas import AirSensorData, SoilSensorData, IrrigationCommand, LedCommand
from yuxi.iot.mqtt_client import MqttClient


class TestMqttClient:

    @patch.dict("os.environ", {"MQTT_ENABLED": "false"})
    def test_disabled_by_default(self):
        client = MqttClient()
        assert client.enabled is False

    @patch.dict("os.environ", {"MQTT_ENABLED": "true"})
    def test_enabled_when_configured(self):
        client = MqttClient()
        assert client.enabled is True

    def test_air_sensor_parsing(self):
        """验证空气传感器数据字段校验与别名映射"""
        payload = {"humidity": 45.5, "temp": 25.3, "co2": 450, "Illumination": 12000}
        data = AirSensorData(**payload)
        assert data.humidity == 45.5
        assert data.temp == 25.3
        assert data.co2 == 450
        assert data.illumination == 12000  # 别名 Illumination -> illumination

    def test_soil_sensor_parsing(self):
        """验证土壤传感器全字段解析"""
        payload = {
            "soil_moisture": 65.5,
            "soil_temperature": 23.8,
            "soil_conductivity": 1200,
            "ph_value": 6.8,
            "nitrogen": 120,
            "phosphorus": 80,
            "potassium": 200,
        }
        data = SoilSensorData(**payload)
        assert data.ph_value == 6.8
        assert data.nitrogen == 120
        assert data.potassium == 200

    def test_irrigation_command_start(self):
        cmd = IrrigationCommand(action="start")
        assert json.loads(cmd.model_dump_json()) == {"action": "start"}

    def test_irrigation_command_stop(self):
        cmd = IrrigationCommand(action="stop")
        assert json.loads(cmd.model_dump_json()) == {"action": "stop"}

    def test_led_single_channel(self):
        """LED 指令只包含指定通道"""
        cmd = LedCommand(led3="on")
        payload = json.loads(cmd.model_dump_json(exclude_none=True))
        assert payload == {"led3": "on"}

    def test_led_multi_channel(self):
        """LED 指令可以同时控制多路"""
        cmd = LedCommand(led1="on", led2="on", led3="off")
        payload = json.loads(cmd.model_dump_json(exclude_none=True))
        assert payload == {"led1": "on", "led2": "on", "led3": "off"}

    def test_led_invalid_value_rejected(self):
        """非法值应被 Pydantic 拒绝"""
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LedCommand(led1="invalid")
