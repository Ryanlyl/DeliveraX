// Mock API for development and presentation

export interface MockUser {
  id: string | number
  username: string
  email: string
  avatar?: string
}

export interface MockLoginResponse {
  token: string
  user: MockUser
}

// Mock users for demonstration
export const MOCK_USERS = {
  admin: {
    username: 'admin',
    password: 'admin123',
    user: {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=admin',
    },
  },
  user: {
    username: 'user',
    password: 'user123',
    user: {
      id: 2,
      username: 'user',
      email: 'user@example.com',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=user',
    },
  },
  demo: {
    username: 'demo',
    password: 'demo123',
    user: {
      id: 3,
      username: 'demo',
      email: 'demo@example.com',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=demo',
    },
  },
}

// Mock login function
export const mockLogin = async (
  username: string,
  password: string
): Promise<MockLoginResponse> => {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 500))

  // Find matching user
  const userEntry = Object.values(MOCK_USERS).find(
    (u) => u.username === username && u.password === password
  )

  if (!userEntry) {
    throw new Error('Invalid username or password')
  }

  // Generate mock token
  const token = `mock_token_${userEntry.user.id}_${Date.now()}`

  return {
    token,
    user: userEntry.user,
  }
}

// Check if mock mode is enabled
export const isMockMode = (): boolean => {
  return true
}

