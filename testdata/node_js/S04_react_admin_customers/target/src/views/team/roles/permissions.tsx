import { useEffect, useState } from 'react'
import { Button, Card, Checkbox, Col, Row, Skeleton, Space, Typography, message } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { getRoleDetail, updateRolePermissions } from '../../../utils/mockData'
import type { Permission, RoleDetail } from '../types'

const groupPermissions = (permissions: Permission[]) => {
  return permissions.reduce<Record<string, Permission[]>>((acc, perm) => {
    if (!acc[perm.category]) acc[perm.category] = []
    acc[perm.category].push(perm)
    return acc
  }, {})
}

const RolePermissionsPage = () => {
  const { roleId } = useParams()
  const [role, setRole] = useState<RoleDetail>()
  const [permissions, setPermissions] = useState<Permission[]>([])
  const [saving, setSaving] = useState(false)
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
        setPermissions(result.permissions)
      } catch (error) {
        console.error(error)
        message.error('Failed to load role permissions')
      } finally {
        setLoading(false)
      }
    }
    loadRole()
  }, [roleId, navigate])

  const handleToggle = (permissionId: string, enabled: boolean) => {
    setPermissions(prev =>
      prev.map(permission => (permission.id === permissionId ? { ...permission, enabled } : permission)),
    )
  }

  const handleSave = async () => {
    if (!roleId) return
    setSaving(true)
    try {
      const updated = await updateRolePermissions(roleId, permissions)
      setRole(updated)
      message.success('Permissions updated')
    } catch (error) {
      console.error(error)
      message.error('Failed to update permissions')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (!role) return
    setPermissions(role.permissions)
  }

  if (loading) {
    return <Skeleton active paragraph={{ rows: 8 }} />
  }

  if (!role) {
    return <Typography.Text type="secondary">Select a role to configure permissions.</Typography.Text>
  }

  const grouped = groupPermissions(permissions)

  return (
    <Card
      title={`Permissions · ${role.name}`}
      extra={
        <Space>
          <Button onClick={handleReset}>Reset</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            Save Changes
          </Button>
        </Space>
      }
    >
      <Row gutter={[24, 24]}>
        {Object.entries(grouped).map(([category, items]) => (
          <Col xs={24} lg={12} key={category}>
            <Typography.Title level={5}>{category}</Typography.Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              {items.map(permission => (
                <div
                  key={permission.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 16px',
                    border: '1px solid var(--ant-color-border-secondary)',
                    borderRadius: 8,
                  }}
                >
                  <div>
                    <Typography.Text strong>{permission.name}</Typography.Text>
                    <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
                      {permission.description}
                    </Typography.Paragraph>
                  </div>
                  <Checkbox
                    checked={permission.enabled}
                    onChange={event => handleToggle(permission.id, event.target.checked)}
                  />
                </div>
              ))}
            </Space>
          </Col>
        ))}
      </Row>
    </Card>
  )
}

export default RolePermissionsPage

