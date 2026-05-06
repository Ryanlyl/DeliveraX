import { Card, Space, Typography } from 'antd'
import { Outlet } from 'react-router-dom'

const TeamLayout = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Team & Access Control
        </Typography.Title>
        <Typography.Text type="secondary">
          Manage roles, permissions, and collaboration policies for your workspace.
        </Typography.Text>
      </Card>
      <Outlet />
    </Space>
  )
}

export default TeamLayout

