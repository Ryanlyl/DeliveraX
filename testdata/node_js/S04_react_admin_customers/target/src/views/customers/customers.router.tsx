import { TeamOutlined } from '@ant-design/icons'
import { AdminRouterItem } from '../../router'
import CustomersPage from '.'

const customersRoutes: AdminRouterItem[] = [
  {
    path: 'customers',
    element: <CustomersPage />,
    meta: {
      label: 'Customers',
      title: 'Customers',
      key: '/customers',
      icon: <TeamOutlined />,
      order: 2,
    },
  },
]

export default customersRoutes

