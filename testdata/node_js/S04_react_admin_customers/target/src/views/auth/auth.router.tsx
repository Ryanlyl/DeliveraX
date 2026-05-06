import { LoginOutlined, UserAddOutlined } from '@ant-design/icons'
import { AdminRouterItem } from '../../router'
import LoginPage from './login'
import RegisterPage from './register'

const authRoutes: AdminRouterItem[] = [
  {
    path: 'auth/login',
    element: <LoginPage />,
    meta: {
      label: 'Login',
      title: 'Login',
      key: '/auth/login',
      icon: <LoginOutlined />,
      hideInMenu: true, // Hide in menu
    },
  },
  {
    path: 'auth/register',
    element: <RegisterPage />,
    meta: {
      label: 'Register',
      title: 'Register',
      key: '/auth/register',
      icon: <UserAddOutlined />,
      hideInMenu: true, // Hide in menu
    },
  },
]

export default authRoutes

