import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { isMockMode, mockLogin } from './mock'

// API base URL, can be read from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage
    const token = localStorage.getItem('token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Return response data directly
    return response.data
  },
  (error) => {
    // Handle error response
    if (error.response) {
      const { status, data } = error.response

      // 401 Unauthorized, clear token and redirect to login page
      if (status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        // Avoid circular redirect
        if (window.location.pathname !== '/auth/login') {
          window.location.href = '/auth/login'
        }
      }

      // Return error message
      return Promise.reject({
        status,
        message: data?.message || error.message || 'Request failed',
        data: data,
      })
    }

    // Network error
    return Promise.reject({
      status: 0,
      message: error.message || 'Network error, please check your network connection',
    })
  }
)

// Request methods wrapper
export const request = {
  get: <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return api.get(url, config)
  },
  post: <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    // Use mock for login in development mode
    if (isMockMode() && url === '/auth/login' && data && typeof data === 'object' && 'username' in data && 'password' in data) {
      return mockLogin(String(data.username), String(data.password)) as Promise<T>
    }
    return api.post(url, data, config) as Promise<T>
  },
  put: <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    return api.put(url, data, config)
  },
  delete: <T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return api.delete(url, config)
  },
  patch: <T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    return api.patch(url, data, config)
  },
}

export default api

