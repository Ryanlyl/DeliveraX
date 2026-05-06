import { DashboardOutlined } from '@ant-design/icons'
import { AdminRouterItem } from '../../router'
import DashboardPage from '.'

const dashboardRoutes: AdminRouterItem[] = [
  {
    path: 'dashboard',
    element: <DashboardPage />,
    meta: {
      label: 'Dashboard',
      title: 'Dashboard',
      key: '/dashboard',
      icon: <DashboardOutlined />,
      order: 1,
    },
  },
]

export default dashboardRoutes

