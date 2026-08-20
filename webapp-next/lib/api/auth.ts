export interface AuthToken {
  access_token: string;
  token_type: 'bearer';
  expires_at: number;
}

export class AuthManager {
  private token: AuthToken | null = null;

  setToken(token: AuthToken): void { this.token = token; }

  getToken(): AuthToken | null { return this.token; }

  getBearer(): string | null { return this.token?.access_token ?? null; }

  isExpired(): boolean {
    if (!this.token) return true;
    return Date.now() >= this.token.expires_at;
  }

  clear(): void { this.token = null; }
}

export const authManager = new AuthManager();
export default AuthToken;