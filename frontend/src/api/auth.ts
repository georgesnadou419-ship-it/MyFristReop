import request from './request'
import type { LoginPayload, LoginResponse, UserInfo } from '../types'

export const loginApi = (payload: LoginPayload) =>
  request.post<unknown, LoginResponse>('/auth/login', payload)

export const meApi = () => request.get<unknown, UserInfo>('/auth/me')
