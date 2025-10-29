import React, { useState } from 'react';
import Head from 'next/head';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/router';
import { BrandMark } from '@/components/BrandMark';
import { Mascot } from '@/components/Mascot';
import { SaffronButton } from '@/components/SaffronButton';
import { Field } from '@/components/Field';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Validate inputs
      if (!email || !password) {
        setError('Please enter both email and password');
        setIsLoading(false);
        return;
      }

      // Call login API
      await login({ email, password });

      // Redirect to home page
      router.push('/home');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to sign in. Please try again.';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };



  return (
    <>
      <Head>
        <title>Sign In - ChandraHoro</title>
        <meta name="description" content="Sign in to your ChandraHoro account" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      {/* Full Viewport Two Column Layout: Image Left (50%), Login Form Right (50%) */}
      <div className="flex flex-col lg:flex-row min-h-screen w-full">
        {/* Left Section: Login Page Image - 50% Width */}
        <div className="flex-1 w-full lg:w-1/2 h-64 lg:h-screen overflow-hidden relative bg-gradient-to-br from-saffron-50 to-orange-50 dark:from-saffron-900/20 dark:to-orange-900/20">
          <Image
            src="/images/loginpage.png"
            alt="ChandraHoro - Login Page"
            width={800}
            height={600}
            className="w-full h-full object-cover object-center"
            priority
          />
        </div>

        {/* Right Section: Login Form - 50% Width */}
        <div className="flex-1 w-full lg:w-1/2 h-auto lg:h-screen flex items-center justify-center p-6 lg:p-10 bg-white dark:bg-gray-900">
          <div className="w-full max-w-lg">
            {/* Logo */}
            <div className="mb-8 text-center lg:text-left">
              <Link href="/">
                <BrandMark size="md" showText={true} />
              </Link>
            </div>

            {/* Login Form Container */}
            <div className="space-y-6">
              <h1 className="font-poppins text-2xl md:text-3xl font-bold text-charcoal dark:text-white mb-2">
                Welcome Back
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-8">
                Sign in to your account to continue
              </p>

              {/* Error message */}
              {error && (
                <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
                </div>
              )}

              {/* Login form */}
              <form onSubmit={handleSubmit} className="space-y-6">
                <Field
                  label="Email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />

                <Field
                  label="Password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                {/* Forgot password link */}
                <div className="flex justify-end">
                  <Link
                    href="/forgot-password"
                    className="text-sm text-saffron-600 dark:text-saffron-400 hover:underline"
                  >
                    Forgot password?
                  </Link>
                </div>

                {/* Sign in button */}
                <SaffronButton
                  variant="primary"
                  size="lg"
                  className="w-full"
                  isLoading={isLoading}
                  type="submit"
                >
                  Sign In
                </SaffronButton>
              </form>

              {/* Divider */}
              <div className="my-8 flex items-center gap-4">
                <div className="flex-1 h-px bg-gray-300 dark:bg-gray-600" />
                <span className="text-sm text-gray-500 dark:text-gray-400">or continue with</span>
                <div className="flex-1 h-px bg-gray-300 dark:bg-gray-600" />
              </div>

              {/* SSO buttons */}
              <div className="grid grid-cols-3 gap-4">
                <button className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border-2 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                </button>
                <button className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border-2 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                  </svg>
                </button>
                <button className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border-2 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-900/30 transition-colors">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                </button>
              </div>

              {/* Sign up link */}
              <p className="text-center text-sm text-gray-600 dark:text-gray-400 mt-8">
                Don't have an account?{' '}
                <Link href="/register" className="text-saffron-600 dark:text-saffron-400 font-600 hover:underline">
                  Sign Up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

