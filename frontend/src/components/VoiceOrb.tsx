import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Loader2 } from 'lucide-react';

interface VoiceOrbProps {
  isListening: boolean;
  isProcessing: boolean;
  onToggle: () => void;
}

export default function VoiceOrb({
  isListening,
  isProcessing,
  onToggle,
}: VoiceOrbProps): React.ReactElement {
  const orbColor = isProcessing
    ? '#7b2fff'
    : isListening
    ? '#00d4ff'
    : '#0084ff';

  const ringColor = isProcessing
    ? 'rgba(123,47,255,0.3)'
    : isListening
    ? 'rgba(0,212,255,0.3)'
    : 'rgba(0,132,255,0.15)';

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Outer glow rings */}
      <div className="relative flex items-center justify-center">
        <AnimatePresence>
          {isListening && (
            <>
              {[1, 2, 3].map((i) => (
                <motion.div
                  key={i}
                  className="absolute rounded-full border"
                  style={{
                    width: 140 + i * 50,
                    height: 140 + i * 50,
                    borderColor: ringColor,
                  }}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{
                    opacity: [0.6, 0, 0.6],
                    scale: [1, 1.2, 1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    delay: i * 0.4,
                    ease: 'easeInOut',
                  }}
                />
              ))}
            </>
          )}
        </AnimatePresence>

        {/* Main orb */}
        <motion.button
          onClick={onToggle}
          className="relative z-10 w-36 h-36 rounded-full flex items-center justify-center cursor-pointer"
          style={{
            background: `radial-gradient(circle at 35% 35%, ${orbColor}cc, ${orbColor}66, #020b18)`,
            boxShadow: `0 0 40px ${ringColor}, 0 0 80px ${ringColor}, inset 0 0 40px rgba(0,0,0,0.5)`,
          }}
          animate={{
            scale: isListening ? [1, 1.05, 1] : 1,
            boxShadow: isListening
              ? [
                  `0 0 40px ${ringColor}, 0 0 80px ${ringColor}`,
                  `0 0 60px ${ringColor}, 0 0 120px ${ringColor}`,
                  `0 0 40px ${ringColor}, 0 0 80px ${ringColor}`,
                ]
              : `0 0 20px ${ringColor}`,
          }}
          transition={{
            duration: 2,
            repeat: isListening ? Infinity : 0,
            ease: 'easeInOut',
          }}
          whileTap={{ scale: 0.95 }}
        >
          {/* Inner hex grid pattern */}
          <div
            className="absolute inset-0 rounded-full opacity-20"
            style={{
              backgroundImage: `repeating-linear-gradient(
                0deg, transparent, transparent 10px, ${orbColor}30 10px, ${orbColor}30 11px
              ), repeating-linear-gradient(
                90deg, transparent, transparent 10px, ${orbColor}30 10px, ${orbColor}30 11px
              )`,
            }}
          />

          {/* Icon */}
          <AnimatePresence mode="wait">
            {isProcessing ? (
              <motion.div
                key="processing"
                initial={{ opacity: 0, rotate: -90 }}
                animate={{ opacity: 1, rotate: 0 }}
                exit={{ opacity: 0 }}
              >
                <Loader2 size={40} color={orbColor} className="animate-spin" />
              </motion.div>
            ) : isListening ? (
              <motion.div
                key="listening"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.5 }}
              >
                <Mic size={40} color={orbColor} />
              </motion.div>
            ) : (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <MicOff size={40} color="#4a7090" />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.button>
      </div>

      {/* Status label */}
      <motion.p
        className="font-display text-xs tracking-widest uppercase"
        style={{ color: orbColor }}
        animate={{ opacity: [1, 0.6, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {isProcessing ? 'Processing...' : isListening ? 'Listening' : 'Tap to Activate'}
      </motion.p>
    </div>
  );
}
