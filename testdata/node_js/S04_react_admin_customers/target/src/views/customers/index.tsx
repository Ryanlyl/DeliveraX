import { useEffect, useMemo, useState } from 'react'
import { Button, Card, DatePicker, Form, Input, Select, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined } from '@ant-design/icons'
import { Customer, CustomerFilters, CustomerSource, CustomerStatus } from './types'
import { createCustomer, deleteCustomer, getCustomers, updateCustomer } from '../../utils/mockData'
import CustomerForm from './components/CustomerForm'
import CustomerDetail from './components/CustomerDetail'

const { RangePicker } = DatePicker

const statusOptions = Object.values(CustomerStatus).map(status => ({
  label: {
    [CustomerStatus.Prospect]: 'Prospect',
    [CustomerStatus.InProgress]: 'In Progress',
    [CustomerStatus.Active]: 'Active',
    [CustomerStatus.Churned]: 'Churned',
  }[status],
  value: status,
}))

const statusColorMap: Record<CustomerStatus, string> = {
  [CustomerStatus.Prospect]: 'default',
  [CustomerStatus.InProgress]: 'processing',
  [CustomerStatus.Active]: 'success',
  [CustomerStatus.Churned]: 'error',
}

const sourceOptions = Object.values(CustomerSource).map(source => ({
  label: {
    [CustomerSource.Website]: 'Website',
    [CustomerSource.Referral]: 'Referral',
    [CustomerSource.Ads]: 'Ads',
    [CustomerSource.Partner]: 'Partner',
    [CustomerSource.Other]: 'Other',
  }[source],
  value: source,
}))

const CustomersPage = () => {
  const [loading, setLoading] = useState(false)
  const [customers, setCustomers] = useState<Customer[]>([])
  const [filters, setFilters] = useState<CustomerFilters>({})
  const [formVisible, setFormVisible] = useState(false)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer>()
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [pagination, setPagination] = useState({ current: 1, pageSize: 10 })

  const loadCustomers = async () => {
    setLoading(true)
    try {
      const data = await getCustomers()
      setCustomers(data)
    } catch (error) {
      console.error(error)
      message.error('Failed to load customers. Please try again later.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCustomers()
  }, [])

  const filteredCustomers = useMemo(() => {
    return customers.filter(customer => {
      if (filters.keyword) {
        const keyword = filters.keyword.toLowerCase()
        const hit = [customer.name, customer.company, customer.email, customer.owner, customer.phone].some(
          field => field?.toLowerCase().includes(keyword),
        )
        if (!hit) return false
      }
      if (filters.status && filters.status.length > 0 && !filters.status.includes(customer.status)) {
        return false
      }
      if (filters.source && filters.source.length > 0 && !filters.source.includes(customer.source)) {
        return false
      }
      if (filters.dateRange) {
        const createdAt = new Date(customer.createdAt).getTime()
        const [start, end] = filters.dateRange
        if (createdAt < new Date(start).getTime() || createdAt > new Date(end).getTime()) {
          return false
        }
      }
      return true
    })
  }, [customers, filters])

  const paginatedData = useMemo(() => {
    const start = (pagination.current - 1) * pagination.pageSize
    return filteredCustomers.slice(start, start + pagination.pageSize)
  }, [filteredCustomers, pagination])

  const handleDelete = async (record: Customer) => {
    try {
      await deleteCustomer(record.id)
      message.success('Customer deleted')
      loadCustomers()
    } catch (error) {
      console.error(error)
      message.error('Failed to delete customer. Please try again later.')
    }
  }

  const handleStatusChange = async (record: Customer, status: CustomerStatus) => {
    try {
      await updateCustomer(record.id, { status })
      message.success('Status updated')
      loadCustomers()
    } catch (error) {
      console.error(error)
      message.error('Failed to update status. Please try again later.')
    }
  }

  const columns: ColumnsType<Customer> = [
    {
      title: 'Customer',
      dataIndex: 'name',
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text strong>{record.name}</Typography.Text>
          <Typography.Text type="secondary">{record.company}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Contact',
      dataIndex: 'email',
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Typography.Text>{record.email}</Typography.Text>
          <Typography.Text type="secondary">{record.phone}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Source / Owner',
      render: (_value, record) => (
        <Space direction="vertical" size={0}>
          <Tag>{sourceOptions.find(option => option.value === record.source)?.label}</Tag>
          <Typography.Text type="secondary">{record.owner ?? 'Unassigned'}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (_value, record) => (
        <Select
          size="small"
          value={record.status}
          style={{ minWidth: 120 }}
          options={statusOptions}
          onChange={status => handleStatusChange(record, status)}
        />
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'createdAt',
      render: value => new Date(value).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_value, record) => (
        <Space>
          <Button
            type="link"
            onClick={() => {
              setSelectedCustomer(record)
              setDetailVisible(true)
            }}
          >
            View
          </Button>
          <Button
            type="link"
            onClick={() => {
              setSelectedCustomer(record)
              setFormMode('edit')
              setFormVisible(true)
            }}
          >
            Edit
          </Button>
          <Button type="link" danger onClick={() => handleDelete(record)}>
            Delete
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
              source: values.source,
              dateRange: values.dateRange
                ? [values.dateRange[0].toISOString(), values.dateRange[1].toISOString()]
                : undefined,
            })
          }}
        >
          <Form.Item name="keyword" label="Keywords">
            <Input
              allowClear
              placeholder="Search name/company/email/owner/phone"
              style={{ width: 260 }}
            />
          </Form.Item>
          <Form.Item name="status" label="Status">
            <Select
              mode="multiple"
              allowClear
              placeholder="Select statuses"
              options={statusOptions}
              style={{ minWidth: 180 }}
            />
          </Form.Item>
          <Form.Item name="source" label="Source">
            <Select
              mode="multiple"
              allowClear
              placeholder="Select sources"
              options={sourceOptions}
              style={{ minWidth: 200 }}
            />
          </Form.Item>
          <Form.Item name="dateRange" label="Created At">
            <RangePicker />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                Search
              </Button>
              <Button
                onClick={() => {
                  setFilters({})
                }}
              >
                Reset
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card
        title="Customers"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setFormMode('create')
              setSelectedCustomer(undefined)
              setFormVisible(true)
            }}
          >
            New Customer
          </Button>
        }
      >
        <Table
          rowKey="id"
          loading={loading}
          dataSource={paginatedData}
          columns={columns}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: filteredCustomers.length,
            showSizeChanger: true,
            onChange: (page, pageSize) => setPagination({ current: page, pageSize }),
          }}
        />
      </Card>

      {formVisible && (
        <CustomerForm
          mode={formMode}
          open={formVisible}
          initialValues={selectedCustomer}
          onCancel={() => setFormVisible(false)}
          onSubmit={async values => {
            try {
              if (formMode === 'create') {
                await createCustomer(values)
                message.success('Customer created successfully')
              } else if (selectedCustomer?.id) {
                await updateCustomer(selectedCustomer.id, values)
                message.success('Customer updated')
              }
              setFormVisible(false)
              loadCustomers()
            } catch (error) {
              console.error(error)
              message.error('Failed to save customer. Please try again later.')
            }
          }}
        />
      )}

      <CustomerDetail
        customer={selectedCustomer}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
        statusRender={(status) => (
          <Tag color={statusColorMap[status]}>
            {statusOptions.find(option => option.value === status)?.label}
          </Tag>
        )}
      />
    </Space>
  )
}

export default CustomersPage

