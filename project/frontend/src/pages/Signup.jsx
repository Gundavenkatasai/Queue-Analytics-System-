import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, Lock, Mail, User, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { GoogleLogin } from '@react-oauth/google';

const Signup = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { register, googleLogin } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setSubmitting(true);
    const result = await register(name, email, password);
    setSubmitting(false);

    if (result.success) {
      navigate('/');
    } else {
      setError(result.error || 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background relative overflow-hidden py-12">
      {/* Background decorations */}
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-accent/20 blur-[120px] rounded-full pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="glass-card w-full max-w-md p-8 rounded-2xl relative z-10"
      >
        <div className="flex justify-center mb-8">
          <div className="bg-primary/20 p-3 rounded-xl">
            <Shield className="w-10 h-10 text-primary" />
          </div>
        </div>
        
        <h2 className="text-3xl font-bold text-white text-center mb-2">Create Account</h2>
        <p className="text-gray-400 text-center mb-8">Join the enterprise surveillance platform</p>

        {/* Error Banner */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start space-x-3 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 mb-5"
          >
            <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
            <p className="text-red-400 text-sm">{error}</p>
          </motion.div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="relative">
            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
            <input 
              type="text" 
              placeholder="Full Name" 
              className="input-field pl-10"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={submitting}
            />
          </div>

          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
            <input 
              type="email" 
              placeholder="Email address" 
              className="input-field pl-10"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={submitting}
            />
          </div>
          
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
            <input 
              type="password" 
              placeholder="Password (min 6 characters)" 
              className="input-field pl-10"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={submitting}
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 w-5 h-5" />
            <input 
              type="password" 
              placeholder="Confirm Password" 
              className="input-field pl-10"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={submitting}
            />
          </div>
          
          <button
            type="submit"
            className="btn-primary flex items-center justify-center space-x-2"
            disabled={submitting}
          >
            {submitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Creating Account...</span>
              </>
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
        
        <div className="mt-6 flex items-center justify-between">
          <span className="w-1/5 border-b border-gray-700"></span>
          <span className="text-xs text-center text-gray-500 uppercase">Or register with</span>
          <span className="w-1/5 border-b border-gray-700"></span>
        </div>
        
        <div className="mt-6 flex justify-center">
          <GoogleLogin 
            onSuccess={credentialResponse => {
              googleLogin(credentialResponse);
              navigate('/');
            }}
            onError={() => {
              setError('Google sign-in failed. Please try again.');
            }}
            prompt="select_account"
            useOneTap={false}
          />
        </div>
        
        <p className="mt-8 text-center text-gray-400 text-sm">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:text-primary/80 transition-colors font-medium">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
};

export default Signup;
