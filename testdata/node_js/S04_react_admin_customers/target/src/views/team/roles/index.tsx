import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Form, Input, Select, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getRoles } from '../../../utils/mockData'
import type { Role } from '../types'

const statusColors: Record<Role['status'], string> = {
  active: 'green',
  pending: 'gold',
  deprecated: 'red',
}

const RolesPage = () => {
  const [loading, setLoading] = useState(false)
  const [roles, setRoles] = useState<Role[]>([])
  const [filters, setFilters] = useState<{ keyword?: string; status?: Role['status'][] }>({})
  const navigate = useNavigate()

  useEffect(() => {
    const loadRoles = async () => {
      setLoading(true)
      try {
        const result = await getRoles()
        setRoles(result)
      } catch (error) {
        console.error(error)
        message.error('Failed to load roles.')
      } finally {
        setLoading(false)
      }
    }
    loadRoles()
  }, [])

  const filteredRoles = useMemo(() => {
    return roles.filter(role => {
      if (filters.keyword) {
        const keyword = filters.keyword.toLowerCase()
        const match = [role.name, role.description].some(field => field?.toLowerCase().includes(keyword))
        if (!match) return false
      }
      if (filters.status && filters.status.length > 0 && !filters.status.includes(role.status)) {
        return false
      }
      return true
    })
  }, [roles, filters])

  const columns: ColumnsType<Role> = [
    {
      title: 'Role',
      dataIndex: 'name',
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{record.name}</Typography.Text>
          <Typography.Text type="secondary">{record.description}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Members',
      dataIndex: 'memberCount',
      width: 120,
    },
    {
      title: 'Permissions',
      dataIndex: 'permissionCount',
      width: 150,
      render: (value: number) => `${value} scopes`,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      width: 140,
      render: (value: Role['status']) => (
        <Tag color={statusColors[value]} style={{ textTransform: 'capitalize' }}>
          {value}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 220,
      render: (_value, record) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/team/role/${record.id}`)}>
            View
          </Button>
          <Button type="link" onClick={() => navigate(`/team/role/${record.id}/permissions`)}>
            Permissions
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Form
          layout="inline"
          style={{ rowGap: 16, columnGap: 16, width: '100%' }}
          onFinish={values => {
            setFilters({
              keyword: values.keyword,
              status: values.status,
            })
          }}
        >
          <Form.Item name="keyword" label="Keyword">
            <Input allowClear placeholder="Search role or description" style={{ width: 240 }} />
          </Form.Item>
          <Form.Item name="status" label="Status">
            <Select
              mode="multiple"
              allowClear
              placeholder="Select status"
              style={{ minWidth: 200 }}
              options={[
                { label: 'Active', value: 'active' },
                { label: 'Pending', value: 'pending' },
                { label: 'Deprecated', value: 'deprecated' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Search
              </Button>
              <Button onClick={() => setFilters({})}>Reset</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title="Roles"
        extra={
          <Button type="primary" icon={<PlusOutlined />}>
            New Role
          </Button>
        }
      >
        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={filteredRoles}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </Space>
  )
}

export default RolesPage

