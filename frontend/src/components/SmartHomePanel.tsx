import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Home, Lightbulb, Thermometer, Lock, Camera, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { useNexusStore } from '../store';
import axios from 'axios';

const DEVICE_ICONS: Record<string, React.ReactNode> = {
  light: <Lightbulb size={16} />,
  thermostat: <Thermometer size={16} />,
  lock: <Lock size={16} />,
  camera: <Camera size={16} />,
  default: <Home size={16} />,
};

const DEMO_DEVICES = [
  { id: 'light-1', name: 'Living Room Light', type: 'light', state: { on: true, brightness: 80 }, online: true },
  { id: 'thermostat-1', name: 'Main Thermostat', type: 'thermostat', state: { temp: 22, mode: 'heat' }, online: true },
  { id: 'lock-front', name: 'Front Door', type: 'lock', state: { locked: true }, online: true },
  { id: 'camera-1', name: 'Security Cam', type: 'camera', state: { recording: false }, online: false },
];

export default function SmartHomePanel(): React.ReactElement {
  const { iotDevices, setIoTDevices } = useNexusStore();
  const [loading, setLoading] = useState(false);

  const devices = iotDevices.length > 0 ? iotDevices : DEMO_DEVICES;

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get('/api/v1/iot/devices');
      if (data.length > 0) setIoTDevices(data);
    } catch {
      /* use demo data */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const toggleDevice = async (deviceId: string, currentState: Record<string, unknown>) => {
    const command = currentState.on !== undefined ? (currentState.on ? 'turn_off' : 'turn_on') : 'toggle';
    try {
      await axios.post(`/api/v1/iot/control?device_id=${deviceId}&command=${command}`);
      await fetchDevices();
    } catch {
      /* offline mode */
    }
  };

  return (
    <div className="nexus-panel">
      <div className="flex items-center justify-between px-4 py-3 border-b border-nexus-border">
        <div className="flex items-center gap-2">
          <Home size={14} className="text-nexus-blue" />
          <span className="font-display text-xs text-nexus-blue tracking-widest uppercase">
            Smart Home
          </span>
        </div>
        <button onClick={fetchDevices} className="text-nexus-dim hover:text-nexus-cyan transition-colors">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="p-3 grid grid-cols-2 gap-2">
        {devices.map((device) => {
          const isOn = device.state.on === true || device.state.locked === false;
          const icon = DEVICE_ICONS[device.type] ?? DEVICE_ICONS.default;

          return (
            <motion.button
              key={device.id}
              onClick={() => toggleDevice(device.id, device.state)}
              className={`relative p-3 rounded-lg border text-left transition-all duration-200 ${
                device.online
                  ? isOn
                    ? 'bg-nexus-cyan/10 border-nexus-cyan/50'
                    : 'bg-nexus-bg border-nexus-border'
                  : 'bg-nexus-bg border-nexus-border/30 opacity-50'
              }`}
              whileTap={{ scale: 0.97 }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={isOn ? 'text-nexus-cyan' : 'text-nexus-dim'}>{icon}</span>
                {device.online ? (
                  <Wifi size={10} className="text-nexus-cyan/60" />
                ) : (
                  <WifiOff size={10} className="text-nexus-dim/40" />
                )}
              </div>
              <p className="text-nexus-text text-xs font-mono truncate">{device.name}</p>
              <p className="text-nexus-dim text-xs mt-0.5">
                {device.online
                  ? Object.entries(device.state)
                      .slice(0, 1)
                      .map(([k, v]) => `${k}: ${v}`)
                      .join(', ')
                  : 'Offline'}
              </p>
              {isOn && device.online && (
                <motion.div
                  className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-nexus-cyan"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
