import React, { useState, useEffect, useMemo } from 'react'
import { Form, Input, Button, Card, message, Typography, Space, Divider, theme } from 'antd'
import { UserOutlined, LockOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import useUserStore from '../../../store/user'
import { request } from '../../../utils/api'
import { MOCK_USERS, isMockMode } from '../../../utils/mock'

const { Title, Text } = Typography

interface LoginFormValues {
  username: string
  password: string
}

interface LoginResponse {
  token: string
  user: {
    id: string | number
    username: string
    email: string
    avatar?: string
  }
}

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const login = useUserStore((state) => state.login)
  const mockEnabled = isMockMode()
  const { token } = theme.useToken()

  const toRgba = (color: string, alpha: number) => {
    if (!color) return `rgba(0,0,0,${alpha})`
    if (color.startsWith('rgb')) {
      return color.replace('rgb', 'rgba').replace(')', `, ${alpha})`)
    }
    let hex = color.replace('#', '')
    if (hex.length === 3) {
      hex = hex.split('').map((char) => char + char).join('')
    }
    const bigint = parseInt(hex, 16)
    const r = (bigint >> 16) & 255
    const g = (bigint >> 8) & 255
    const b = bigint & 255
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }

  const backgroundStyle = useMemo(() => ({
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: token.colorBgLayout,
    backgroundImage: `
      radial-gradient(circle at 15% 20%, ${toRgba(token.colorPrimary, 0.18)}, transparent 55%),
      radial-gradient(circle at 85% 10%, ${toRgba(token.green8, 0.16)}, transparent 50%),
      linear-gradient(0deg, ${toRgba(token.colorSplit, 0.8)} 1px, transparent 1px),
      linear-gradient(90deg, ${toRgba(token.colorSplit, 0.6)} 1px, transparent 1px)
    `,
    backgroundSize: 'auto, auto, 32px 32px, 32px 32px',
    backgroundAttachment: 'fixed'
  }), [token])

  // Auto-fill form in development mode for demo; optional autologin for E2E (mock only)
  useEffect(() => {
    if (!mockEnabled) return
    const urlParams = new URLSearchParams(window.location.search)
    const demoUser = urlParams.get('demo') || 'demo'
    const mockUser = MOCK_USERS[demoUser as keyof typeof MOCK_USERS] || MOCK_USERS.demo
    form.setFieldsValue({
      username: mockUser.username,
      password: mockUser.password,
    })
    if (urlParams.get('autologin') === '1') {
      const id = window.setTimeout(() => form.submit(), 150)
      return () => window.clearTimeout(id)
    }
  }, [form, mockEnabled])

  const onFinish = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      // Call login API
      const response = await request.post<LoginResponse>('/auth/login', {
        username: values.username,
        password: values.password,
      })

      // Login successful, save user info and token
      login(response.user, response.token)

      message.success('Login successful!')
      
      // Redirect to home page or previously visited page
      const redirect = new URLSearchParams(window.location.search).get('redirect') || '/dashboard'
      navigate(redirect)
    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'message' in error 
        ? String(error.message) 
        : 'Login failed, please check your username and password'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleQuickLogin = (userKey: keyof typeof MOCK_USERS) => {
    const mockUser = MOCK_USERS[userKey]
    form.setFieldsValue({
      username: mockUser.username,
      password: mockUser.password,
    })
    form.submit()
  }

  return (
    <div style={backgroundStyle}>
      <Card
        style={{
          width: 400,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={2}>Login</Title>
            <Text type="secondary">Welcome back, please login to your account</Text>
          </div>

          <Form
            name="login"
            form={form}
            onFinish={onFinish}
            autoComplete="off"
            size="large"
            layout="vertical"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: 'Please enter username or email' },
                { min: 3, message: 'Username must be at least 3 characters' },
              ]}
            >
              <Input
                id="username"
                prefix={<UserOutlined />}
                placeholder="Username or email"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: 'Please enter password' },
                { min: 6, message: 'Password must be at least 6 characters' },
              ]}
            >
              <Input.Password
                id="password"
                prefix={<LockOutlined />}
                placeholder="Password"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
              >
                Login
              </Button>
            </Form.Item>
          </Form>

          {mockEnabled && (
            <>
              <Divider plain>Quick Login (Demo)</Divider>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                <Button
                  icon={<ThunderboltOutlined />}
                  onClick={() => handleQuickLogin('demo')}
                  block
                  style={{ marginBottom: 8 }}
                >
                  Login as Demo User
                </Button>
                <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Button
                    size="small"
                    onClick={() => handleQuickLogin('admin')}
                    style={{ flex: 1 }}
                  >
                    Admin
                  </Button>
                  <Button
                    size="small"
                    onClick={() => handleQuickLogin('user')}
                    style={{ flex: 1 }}
                  >
                    User
                  </Button>
                  <Button
                    size="small"
                    onClick={() => handleQuickLogin('demo')}
                    style={{ flex: 1 }}
                  >
                    Demo
                  </Button>
                </Space>
              </Space>
            </>
          )}

          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <Text type="secondary">
              Don't have an account?{' '}
              <Link to="/auth/register">Sign up</Link>
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  )
}

export default LoginPage

