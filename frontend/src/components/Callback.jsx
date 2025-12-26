import React, { useEffect, useState } from 'react';
import { cyberarkAuth } from '../services/cyberark-auth';

export default function Callback() {
  const [status, setStatus] = useState('processing');
  const [error, setError] = useState(null);

  useEffect(() => {
    handleCallback();
  }, []);

  const handleCallback = async () => {
    try {
      setStatus('exchanging');
      await cyberarkAuth.handleCallback();

      setStatus('success');

      // Redirect to main app after short delay
      setTimeout(() => {
        window.location.href = '/';
      }, 1000);

    } catch (err) {
      console.error('OAuth callback error:', err);
      setError(err.message);
      setStatus('error');
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      backgroundColor: '#f5f5f5',
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: 'white',
        padding: '40px',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        maxWidth: '400px',
        width: '100%',
        textAlign: 'center'
      }}>
        {status === 'processing' && (
          <>
            <div style={{
              width: '50px',
              height: '50px',
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #007bff',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }}></div>
            <h2>Processing...</h2>
            <p style={{ color: '#666' }}>Please wait</p>
          </>
        )}

        {status === 'exchanging' && (
          <>
            <div style={{
              width: '50px',
              height: '50px',
              border: '4px solid #f3f3f3',
              borderTop: '4px solid #007bff',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }}></div>
            <h2>Authenticating...</h2>
            <p style={{ color: '#666' }}>Completing sign-in</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div style={{
              width: '50px',
              height: '50px',
              backgroundColor: '#28a745',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              color: 'white',
              fontSize: '24px'
            }}>
              ✓
            </div>
            <h2>Success!</h2>
            <p style={{ color: '#666' }}>Redirecting to app...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <div style={{
              width: '50px',
              height: '50px',
              backgroundColor: '#dc3545',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              color: 'white',
              fontSize: '24px'
            }}>
              ✗
            </div>
            <h2>Authentication Failed</h2>
            <p style={{ color: '#666', marginBottom: '20px' }}>{error}</p>
            <button
              onClick={() => window.location.href = '/'}
              style={{
                padding: '10px 20px',
                backgroundColor: '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Return to Login
            </button>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
