import { useCallback } from 'react'
import { api } from './client.js'
import { useAuth } from '../context/AuthContext.jsx'

// Calls the API with the logged-in user's token. If the token has expired, signs the user out.
export function useApi() {
  const { token, logout } = useAuth()
  return useCallback(
    async (path, options = {}) => {
      try {
        return await api(path, { ...options, token })
      } catch (err) {
        if (err.status === 401) logout()
        throw err
      }
    },
    [token, logout]
  )
}
