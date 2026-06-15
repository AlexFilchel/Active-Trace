export interface LoginTokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

export interface LoginTwoFactorResponse {
  requires_two_factor: true
  challenge_token: string
  expires_in: number
}

export type LoginResponse = LoginTokenResponse | LoginTwoFactorResponse

export interface RefreshResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

export interface JwtClaims {
  sub: string
  tenant_id: string
  roles: string[]
  exp: number
}

export interface SessionState {
  accessToken: string | null
  claims: JwtClaims | null
  isAuthenticated: boolean
}
