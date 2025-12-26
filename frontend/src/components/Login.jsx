import React from 'react';
import { cyberarkAuth } from '../services/cyberark-auth';

export default function Login() {
  const handleLogin = () => {
    cyberarkAuth.login();
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
        <h1 style={{ marginBottom: '10px' }}>Deep Research Agent</h1>
        <p style={{ color: '#666', marginBottom: '30px' }}>
          Sign in with CyberArk to continue
        </p>

        <button
          onClick={handleLogin}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '16px',
            cursor: 'pointer',
            fontWeight: '500'
          }}
          onMouseOver={(e) => e.target.style.backgroundColor = '#0056b3'}
          onMouseOut={(e) => e.target.style.backgroundColor = '#007bff'}
        >
          Sign in with CyberArk
        </button>

        <p style={{
          marginTop: '20px',
          fontSize: '14px',
          color: '#999'
        }}>
          You will be redirected to CyberArk for authentication
        </p>
      </div>
    </div>
  );
}
