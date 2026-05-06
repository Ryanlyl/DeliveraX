import React, { useState, useMemo } from 'react'
import { Form, Input, Button, Card, message, Typography, Space, theme } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useNavigate, Link } from 'react-router-dom'
import { request } from '../../../utils/api'

const { Title, Text } = Typography

interface RegisterFormValues {
  username: string
  email: string
  password: string
  confirmPassword: string
}

interface RegisterResponse {
  message: string
  user?: {
    id: string | number
    username: string
    email: string
  }
}

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
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

  const onFinish = async (values: RegisterFormValues) => {
    setLoading(true)
    try {
      // Call register API
      await request.post<RegisterResponse>('/auth/register', {
        username: values.username,
        email: values.email,
        password: values.password,
      })

      message.success('Registration successful! Please login')
      
      // Redirect to login page
      navigate('/auth/login')
    } catch (error: unknown) {
      const errorMessage = error && typeof error === 'object' && 'message' in error 
        ? String(error.message) 
        : 'Registration failed, please try again'
      message.error(errorMessage)
    } finally {
      setLoading(false)
    }
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
            <Title level={2}>Sign Up</Title>
            <Text type="secondary">Create a new account to get started</Text>
          </div>

          <Form
            name="register"
            onFinish={onFinish}
            autoComplete="off"
            size="large"
            layout="vertical"
          >
            <Form.Item
              name="username"
              rules={[
                { required: true, message: 'Please enter username' },
                { min: 3, message: 'Username must be at least 3 characters' },
                { max: 20, message: 'Username must be at most 20 characters' },
                { pattern: /^[a-zA-Z0-9_]+$/, message: 'Username can only contain letters, numbers and underscores' },
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="Username"
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: 'Please enter email' },
                { type: 'email', message: 'Please enter a valid email address' },
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="Email"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: 'Please enter password' },
                { min: 6, message: 'Password must be at least 6 characters' },
                { max: 20, message: 'Password must be at most 20 characters' },
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Password"
              />
            </Form.Item>

            <Form.Item
              name="confirmPassword"
              dependencies={['password']}
              rules={[
                { required: true, message: 'Please confirm password' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('The two passwords do not match'))
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Confirm Password"
              />
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                block
              >
                Sign Up
              </Button>
            </Form.Item>
          </Form>

          <div style={{ textAlign: 'center' }}>
            <Text type="secondary">
              Already have an account?{' '}
              <Link to="/auth/login">Login</Link>
            </Text>
          </div>
        </Space>
      </Card>
    </div>
  )
}

export default RegisterPage

