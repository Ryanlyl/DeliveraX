import { useEffect, useState } from 'react'
import { Card, Col, Descriptions, List, Row, Skeleton, Space, Statistic, Tag, Typography, message } from 'antd'
import { useParams, useNavigate, Outlet } from 'react-router-dom'
import { getRoleDetail } from '../../../utils/mockData'
import type { RoleDetail } from '../types'

const RoleDetailPage = () => {
  const { roleId } = useParams()
  const [role, setRole] = useState<RoleDetail>()
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const loadRole = async () => {
      if (!roleId) return
      setLoading(true)
      try {
        const result = await getRoleDetail(roleId)
        if (!result) {
          message.error('Role not found')
          navigate('/team/roles')
          return
        }
        setRole(result)
      } catch (error) {
        console.error(error)
        message.error('Failed to load role details')
      } finally {
        setLoading(false)
      }
    }
    loadRole()
  }, [roleId, navigate])

  if (loading) {
    return <Skeleton active paragraph={{ rows: 12 }} />
  }

  if (!role) {
    return <Typography.Text type="secondary">Select a role to view details.</Typography.Text>
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Role Overview">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Name">{role.name}</Descriptions.Item>
              <Descriptions.Item label="Description">{role.description}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={role.status === 'active' ? 'green' : role.status === 'pending' ? 'gold' : 'red'}>
                  {role.status.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Owner">{role.owner}</Descriptions.Item>
              <Descriptions.Item label="Updated">
                {new Date(role.updatedAt).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Usage Metrics">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic title="Members" value={role.memberCount} />
              </Col>
              <Col span={12}>
                <Statistic title="Permissions" value={role.permissionCount} />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Assigned Members" extra={<Typography.Link>Manage</Typography.Link>}>
            <List
              dataSource={role.members}
              renderItem={member => (
                <List.Item>
                  <List.Item.Meta
                    title={member.name}
                    description={member.title}
                  />
                </List.Item>
              )}
              locale={{ emptyText: 'No members assigned yet.' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Recent Activity">
            <List
              dataSource={role.auditLog}
              renderItem={log => (
                <List.Item>
                  <List.Item.Meta
                    title={log.action}
                    description={`${log.actor} · ${new Date(log.timestamp).toLocaleString()}`}
                  />
                </List.Item>
              )}
              locale={{ emptyText: 'No changes recorded.' }}
            />
          </Card>
        </Col>
      </Row>

      <Outlet />
    </Space>
  )
}

export default RoleDetailPage

