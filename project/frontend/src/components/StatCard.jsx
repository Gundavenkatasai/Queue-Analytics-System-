import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BiUpArrowAlt, BiDownArrowAlt } from 'react-icons/bi';
import { FiUsers, FiTrendingUp } from 'react-icons/fi';

const StatCard = ({ label, value, icon: Icon, trend, color = 'blue', unit = '' }) => {
  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 },
    },
  };

  const pulseVariants = {
    pulse: {
      scale: [1, 1.05, 1],
      transition: { duration: 2, repeat: Infinity },
    },
  };

  const colorMap = {
    blue: 'from-blue-500 to-blue-600',
    purple: 'from-purple-500 to-purple-600',
    green: 'from-green-500 to-green-600',
    red: 'from-red-500 to-red-600',
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className={`relative bg-gradient-to-br ${colorMap[color]} rounded-2xl p-6 text-white overflow-hidden shadow-2xl`}
    >
      {/* Background blur effect */}
      <div className="absolute inset-0 backdrop-blur-sm opacity-10"></div>
      
      {/* Content */}
      <div className="relative z-10 flex justify-between items-start">
        <div className="flex-1">
          <p className="text-sm font-medium opacity-90 mb-2">{label}</p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-bold">{value}</h3>
            {unit && <span className="text-sm opacity-80">{unit}</span>}
          </div>
          {trend && (
            <div className="mt-2 flex items-center gap-1">
              {trend > 0 ? (
                <>
                  <BiUpArrowAlt className="text-green-300" />
                  <span className="text-xs text-green-300">{trend}% ↑</span>
                </>
              ) : (
                <>
                  <BiDownArrowAlt className="text-yellow-300" />
                  <span className="text-xs text-yellow-300">{Math.abs(trend)}% ↓</span>
                </>
              )}
            </div>
          )}
        </div>
        <motion.div
          variants={pulseVariants}
          animate="pulse"
          className="text-4xl opacity-80"
        >
          {Icon && <Icon />}
        </motion.div>
      </div>

      {/* Border glow */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-20 transition-opacity duration-500"></div>
    </motion.div>
  );
};

export default StatCard;
