import { useEffect, useMemo, useState } from 'react'
import { Line, Pie } from '@ant-design/charts'
import { ArrowUpOutlined, FireOutlined, TeamOutlined } from '@ant-design/icons'
import { Card, Col, List, Row, Skeleton, Space, Statistic, Tag, Typography, theme } from 'antd'
import useConfigStore from '../../store/config'
import type { DashboardStats } from '../../utils/mockData'
import { getDashboardStats } from '../../utils/mockData'
import { CustomerStatus } from '../customers/types'

const statusLabelMap: Record<CustomerStatus, string> = {
  [CustomerStatus.Prospect]: 'Prospect',
  [CustomerStatus.InProgress]: 'In Progress',
  [CustomerStatus.Active]: 'Active',
  [CustomerStatus.Churned]: 'Churned',
}

const statusColorMap: Record<CustomerStatus, string> = {
  [CustomerStatus.Prospect]: 'default',
  [CustomerStatus.InProgress]: 'processing',
  [CustomerStatus.Active]: 'success',
  [CustomerStatus.Churned]: 'error',
}

const DashboardPage = () => {
  const [stats, setStats] = useState<DashboardStats>()
  const [loading, setLoading] = useState(true)
  const { token } = theme.useToken()
  const algorithms = useConfigStore(state => state.themeConfig._algorithm)
  const isDarkMode = algorithms.includes('dark')

  useEffect(() => {
    let mounted = true
    const load = async () => {
      setLoading(true)
      try {
        const nextStats = await getDashboardStats()
        if (mounted) {
          setStats(nextStats)
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }
    load()
    const timer = setInterval(load, 1000 * 60 * 5)
    return () => {
      mounted = false
      clearInterval(timer)
    }
  }, [])

  const metricCards = useMemo(() => ([
    {
      title: 'Total Customers',
      value: stats?.totalCustomers ?? 0,
      suffix: 'customers',
      icon: <TeamOutlined style={{ color: '#1890ff' }} />,
      trend: '+12% MoM',
    },
    {
      title: 'New Customers (Monthly)',
      value: stats?.newCustomers ?? 0,
      suffix: 'customers',
      icon: <ArrowUpOutlined style={{ color: '#52c41a' }} />,
      trend: '+8% YoY',
    },
    {
      title: 'MRR',
      value: stats?.monthlyRecurringRevenue ?? 0,
      prefix: '¥',
      icon: <FireOutlined style={{ color: '#fa8c16' }} />,
      trend: '+5.6% QoQ',
    },
    {
      title: 'Active Deals',
      value: stats?.activeDeals ?? 0,
      suffix: 'deals',
      icon: <ArrowUpOutlined style={{ color: '#722ed1' }} />,
      trend: '72% win rate',
    },
  ]), [stats])

  const metricCardStyle = {
    background: token.colorBgElevated,
    border: `1px solid ${token.colorBorderSecondary}`,
    borderRadius: token.borderRadiusLG,
  }

  const chartThemeConfig = isDarkMode ? { theme: 'classicDark' } : { theme: 'classic' }

  if (loading && !stats) {
    return <Skeleton active paragraph={{ rows: 12 }} />
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        {metricCards.map(card => (
          <Col key={card.title} xs={24} sm={12} lg={6}>
            <Card styles={{ body: { padding: 16 } }} style={metricCardStyle}>
              <Space align="start">
                {card.icon}
                <Statistic
                  title={card.title}
                  value={card.value}
                  prefix={card.prefix}
                  suffix={card.suffix}
                  valueStyle={{ color: token.colorText }}
                />
              </Space>
              <Typography.Text style={{ color: token.colorTextSecondary }}>{card.trend}</Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="Revenue Trend" extra={<Typography.Text type="secondary">Last 6 months</Typography.Text>}>
            {stats ? (
              <Line
                data={stats.revenueTrend}
                xField="month"
                yField="revenue"
                smooth
                height={320}
                point={{ sizeField: 5 }}
                xAxis={{
                  label: { style: { fill: token.colorTextSecondary } },
                  line: { style: { stroke: token.colorBorderSecondary } },
                  tickLine: { style: { stroke: token.colorBorderSecondary } },
                }}
                yAxis={{
                  label: { style: { fill: token.colorTextSecondary } },
                  grid: { line: { style: { stroke: token.colorSplit, lineDash: [4, 4] } } },
                }}
                tooltip={{
                  formatter: (datum: { revenue: number }) => ({
                    name: 'Revenue',
                    value: `¥${datum.revenue.toLocaleString()}`,
                  }),
                }}
                {...chartThemeConfig}
              />
            ) : (
              <Skeleton active />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Customer Sources">
            {stats ? (
              <Pie
                data={stats.sourceDistribution}
                angleField="value"
                colorField="type"
                innerRadius={0.5}
                height={320}
                legend={{
                  position: 'bottom',
                  itemName: { style: { fill: token.colorTextSecondary } },
                }}
                label={{
                  text: 'value',
                  style: { fontWeight: 600, fill: token.colorText },
                }}
                {...chartThemeConfig}
              />
            ) : (
              <Skeleton active />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Recent Activity">
            <List
              dataSource={stats?.recentActivities ?? []}
              renderItem={activity => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <Space>
                        <Typography.Text strong>{activity.summary}</Typography.Text>
                        {activity.statusAfter && (
                          <Tag color={statusColorMap[activity.statusAfter]}>{statusLabelMap[activity.statusAfter]}</Tag>
                        )}
                      </Space>
                    }
                    description={`${activity.actor} · ${new Date(activity.timestamp).toLocaleString()}`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Health Insights">
            <List
              dataSource={[
                {
                  title: 'Follow-up Reminder',
                  description: 'Four prospects have been idle for over 7 days. Reach out soon to improve conversion.',
                },
                {
                  title: 'Expansion Opportunity',
                  description: 'Atlas Logistics active usage grew 32%. Consider pitching an upgraded plan.',
                },
                {
                  title: 'Renewal Alert',
                  description: 'Two enterprise contracts expire within 30 days. Prepare renewal strategies.',
                },
              ]}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    title={<Typography.Text strong>{item.title}</Typography.Text>}
                    description={item.description}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  )
}

export default DashboardPage

