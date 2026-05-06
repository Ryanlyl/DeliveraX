import { useEffect, useState } from 'react'
import { Form, Input, Modal, Select } from 'antd'
import { Customer, CustomerFormValues, CustomerSource, CustomerStatus } from '../types'

export interface CustomerFormProps {
  mode: 'create' | 'edit'
  open: boolean
  initialValues?: Customer
  onSubmit: (values: CustomerFormValues) => Promise<void> | void
  onCancel: () => void
}

const statusOptions = [
  { label: 'Prospect', value: CustomerStatus.Prospect },
  { label: 'In Progress', value: CustomerStatus.InProgress },
  { label: 'Active', value: CustomerStatus.Active },
  { label: 'Churned', value: CustomerStatus.Churned },
]

const sourceOptions = [
  { label: 'Website', value: CustomerSource.Website },
  { label: 'Referral', value: CustomerSource.Referral },
  { label: 'Ads', value: CustomerSource.Ads },
  { label: 'Partner', value: CustomerSource.Partner },
  { label: 'Other', value: CustomerSource.Other },
]

const CustomerForm = ({ mode, open, initialValues, onSubmit, onCancel }: CustomerFormProps) => {
  const [form] = Form.useForm<CustomerFormValues>()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        name: initialValues?.name,
        email: initialValues?.email,
        phone: initialValues?.phone,
        company: initialValues?.company,
        position: initialValues?.position,
        source: initialValues?.source ?? CustomerSource.Website,
        status: initialValues?.status ?? CustomerStatus.Prospect,
        owner: initialValues?.owner,
        notes: initialValues?.notes,
      })
    } else {
      form.resetFields()
    }
  }, [form, initialValues, open])

  const handleFinish = async (values: CustomerFormValues) => {
    setSubmitting(true)
    try {
      await onSubmit(values)
      form.resetFields()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={mode === 'create' ? 'Create Customer' : 'Edit Customer'}
      open={open}
      onCancel={() => {
        if (!submitting) onCancel()
      }}
      onOk={() => form.submit()}
      confirmLoading={submitting}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={handleFinish}>
        <Form.Item
          name="name"
          label="Name / Company"
          rules={[{ required: true, message: 'Please enter a name' }]}
        >
          <Input placeholder="e.g. Acme Corp" />
        </Form.Item>
        <Form.Item
          name="email"
          label="Email"
          rules={[
            { required: true, message: 'Please enter an email' },
            { type: 'email', message: 'Please enter a valid email' },
          ]}
        >
          <Input placeholder="contact@example.com" />
        </Form.Item>
        <Form.Item name="phone" label="Phone">
          <Input placeholder="+1 415 000 0000" />
        </Form.Item>
        <Form.Item name="company" label="Company">
          <Input placeholder="Company name" />
        </Form.Item>
        <Form.Item name="position" label="Title">
          <Input placeholder="Title" />
        </Form.Item>
        <Form.Item name="source" label="Source" rules={[{ required: true }]}>
          <Select options={sourceOptions} />
        </Form.Item>
        <Form.Item name="status" label="Status" rules={[{ required: true }]}>
          <Select options={statusOptions} />
        </Form.Item>
        <Form.Item name="owner" label="Customer Success Owner">
          <Input placeholder="e.g. Iris Chen" />
        </Form.Item>
        <Form.Item name="notes" label="Notes">
          <Input.TextArea rows={3} placeholder="Additional context or follow-up plan" />
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default CustomerForm

