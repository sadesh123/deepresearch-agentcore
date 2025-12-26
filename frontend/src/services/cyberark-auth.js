/**
 * CyberArk OAuth Authentication Service
 * Handles OAuth 2.0 Authorization Code flow
 */

class CyberArkAuth {
  constructor() {
    this.clientId = import.meta.env.VITE_CYBERARK_CLIENT_ID;
    this.authEndpoint = import.meta.env.VITE_CYBERARK_AUTH_ENDPOINT;
    this.tokenEndpoint = import.meta.env.VITE_CYBERARK_TOKEN_ENDPOINT;
    this.redirectUri = window.location.origin + '/callback';
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    const token = this.getAccessToken();
    if (!token) return false;

    // Check if token is expired
    const expiry = localStorage.getItem('cyberark_token_expiry');
    if (!expiry) return false;

    return Date.now() < parseInt(expiry);
  }

  /**
   * Get stored access token
   */
  getAccessToken() {
    return localStorage.getItem('cyberark_access_token');
  }

  /**
   * Initiate OAuth login flow
   */
  login() {
    // Generate state for CSRF protection
    const state = this.generateRandomString(32);
    sessionStorage.setItem('oauth_state', state);

    // Build authorization URL
    const params = new URLSearchParams({
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      response_type: 'code',
      scope: 'openid profile email',
      state: state
    });

    const authUrl = `${this.authEndpoint}?${params.toString()}`;

    console.log('Redirecting to CyberArk login:', authUrl);
    window.location.href = authUrl;
  }

  /**
   * Handle OAuth callback
   */
  async handleCallback() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    // Check for errors
    if (error) {
      throw new Error(`OAuth error: ${error}`);
    }

    if (!code) {
      throw new Error('No authorization code received');
    }

    // Verify state
    const savedState = sessionStorage.getItem('oauth_state');
    if (state !== savedState) {
      throw new Error('Invalid state parameter - possible CSRF attack');
    }

    // Exchange code for token via backend (secure - client secret not exposed)
    console.log('Exchanging authorization code for token via backend...');

    const tokenExchangeEndpoint = import.meta.env.VITE_API_BASE_URL + '/auth/token';

    const tokenResponse = await fetch(tokenExchangeEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        code: code,
        redirect_uri: this.redirectUri
      })
    });

    if (!tokenResponse.ok) {
      const errorText = await tokenResponse.text();
      throw new Error(`Token exchange failed: ${errorText}`);
    }

    const tokenData = await tokenResponse.json();

    // Store tokens
    this.storeTokens(
      tokenData.access_token,
      tokenData.refresh_token,
      tokenData.expires_in
    );

    // Clean up
    sessionStorage.removeItem('oauth_state');

    console.log('✓ Authentication successful');

    return tokenData.access_token;
  }

  /**
   * Store authentication tokens
   */
  storeTokens(accessToken, refreshToken, expiresIn) {
    const expiryTime = Date.now() + (expiresIn * 1000);

    localStorage.setItem('cyberark_access_token', accessToken);
    localStorage.setItem('cyberark_token_expiry', expiryTime.toString());

    console.log(`Token stored, expires in ${expiresIn} seconds`);
  }

  /**
   * Logout and clear tokens
   */
  logout() {
    localStorage.removeItem('cyberark_access_token');
    localStorage.removeItem('cyberark_token_expiry');
    sessionStorage.removeItem('oauth_state');

    console.log('Logged out');
  }

  /**
   * Generate random string for state parameter
   */
  generateRandomString(length) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    for (let i = 0; i < length; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }
}

// Export singleton instance
export const cyberarkAuth = new CyberArkAuth();
export default cyberarkAuth;
