import { TeamOutlined, SafetyOutlined, SettingOutlined } from '@ant-design/icons'
import type { AdminRouterItem } from '../../router'
import TeamLayout from './teamLayout'
import RolesPage from './roles'
import RoleDetailPage from './roles/detail'
import RolePermissionsPage from './roles/permissions'

const teamRoutes: AdminRouterItem[] = [
  {
    path: 'team',
    element: <TeamLayout />,
    meta: {
      label: 'Team',
      title: 'Team',
      key: '/team',
      icon: <TeamOutlined />,
      order: 3,
    },
    children: [
      {
        path: 'roles',
        element: <RolesPage />,
        meta: {
          label: 'Roles',
          title: 'Roles',
          key: '/team/roles',
          icon: <SafetyOutlined />,
        },
      },
      {
        path: 'role/:roleId',
        element: <RoleDetailPage />,
        meta: {
          label: 'Role Detail',
          title: 'Role Detail',
          key: '/team/role/:roleId',
          icon: <SettingOutlined />,
          hideInMenu: true,
        },
      },
      {
        path: 'role/:roleId/permissions',
        element: <RolePermissionsPage />,
        meta: {
          label: 'Permissions',
          title: 'Role Permissions',
          key: '/team/role/:roleId/permissions',
          icon: <SettingOutlined />,
          hideInMenu: true,
        },
      },
    ],
  },
]

export default teamRoutes

