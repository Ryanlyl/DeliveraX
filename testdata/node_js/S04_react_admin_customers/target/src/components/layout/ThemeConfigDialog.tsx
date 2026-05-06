import { useState, useEffect } from 'react'
import { Modal, Radio, ColorPicker, Space, Divider, Typography, Row, Col, Tabs, InputNumber, Button, Alert } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { Color } from 'antd/es/color-picker'
import useConfigStore from '../../store/config'
import { getAllPresetThemes } from '../../config/theme-presets'
import type { PresetThemeName } from '../../config/theme'
import type { ThemeConfig, SpacingConfig, BorderRadiusConfig, TypographyConfig } from '../../config/theme'

const { Title, Text } = Typography

interface ThemeConfigDialogProps {
  open: boolean
  onClose: () => void
}

const ThemeConfigDialog = ({ open, onClose }: ThemeConfigDialogProps) => {
  const themeConfig = useConfigStore((state) => state.themeConfig)
  const currentPresetTheme = useConfigStore((state) => state.currentPresetTheme)
  const setTheme = useConfigStore((state) => state.setTheme)
  const setCustomColor = useConfigStore((state) => state.setCustomColor)
  const setSpacing = useConfigStore((state) => state.setSpacing)
  const setBorderRadius = useConfigStore((state) => state.setBorderRadius)
  const setTypography = useConfigStore((state) => state.setTypography)
  const resetTheme = useConfigStore((state) => state.resetTheme)
  
  // Check if dark mode is active
  const isDarkMode = themeConfig._algorithm.includes('dark')

  const [selectedPreset, setSelectedPreset] = useState<PresetThemeName | 'custom'>(
    currentPresetTheme || 'custom'
  )
  const [customColors, setCustomColors] = useState<ThemeConfig['colors']>(themeConfig.colors)
  const [customSpacing, setCustomSpacing] = useState<SpacingConfig>(themeConfig.spacing)
  const [customBorderRadius, setCustomBorderRadius] = useState<BorderRadiusConfig>(themeConfig.borderRadius)
  const [customTypography, setCustomTypography] = useState<TypographyConfig>(themeConfig.typography)

  const presetThemes = getAllPresetThemes()

  useEffect(() => {
    if (open) {
      setSelectedPreset(currentPresetTheme || 'custom')
      setCustomColors(themeConfig.colors)
      setCustomSpacing(themeConfig.spacing)
      setCustomBorderRadius(themeConfig.borderRadius)
      setCustomTypography(themeConfig.typography)
    }
  }, [open, currentPresetTheme, themeConfig])

  const handlePresetChange = (presetName: PresetThemeName) => {
    setSelectedPreset(presetName)
    setTheme(presetName)
  }

  const handleCustomColorChange = (colorKey: keyof ThemeConfig['colors'], color: Color) => {
    const hexColor = color.toHexString()
    setCustomColors((prev) => ({
      ...prev,
      [colorKey]: hexColor,
    }))
    setCustomColor(colorKey, hexColor)
    setSelectedPreset('custom')
  }

  const colorLabels: Record<keyof ThemeConfig['colors'], string> = {
    primary: 'Primary',
    secondary: 'Secondary',
    success: 'Success',
    warning: 'Warning',
    error: 'Error',
    info: 'Info',
    background: 'Background',
    text: 'Text',
  }

  const handleSpacingChange = (key: keyof SpacingConfig, value: number | null) => {
    if (value !== null) {
      const newSpacing = { ...customSpacing, [key]: value }
      setCustomSpacing(newSpacing)
      setSpacing({ [key]: value })
    }
  }

  const handleBorderRadiusChange = (key: keyof BorderRadiusConfig, value: number | null) => {
    if (value !== null) {
      const newBorderRadius = { ...customBorderRadius, [key]: value }
      setCustomBorderRadius(newBorderRadius)
      setBorderRadius({ [key]: value })
    }
  }

  const handleTypographyChange = (key: keyof TypographyConfig, value: number | null) => {
    if (value !== null) {
      const newTypography = { ...customTypography, [key]: value }
      setCustomTypography(newTypography)
      setTypography({ [key]: value })
    }
  }

  const handleReset = () => {
    resetTheme()
  }

  const renderColorsTab = () => (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={5}>Preset Themes</Title>
        <Radio.Group
          value={selectedPreset}
          onChange={(e) => {
            const value = e.target.value
            if (value === 'custom') {
              setSelectedPreset('custom')
            } else {
              handlePresetChange(value as PresetThemeName)
            }
          }}
          style={{ width: '100%' }}
        >
          <Row gutter={[16, 16]}>
            {presetThemes.map((preset) => (
              <Col span={8} key={preset.name}>
                <Radio value={preset.name} style={{ width: '100%' }}>
                  <Space>
                    <div
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: 4,
                        backgroundColor: preset.colors.primary,
                        border: '1px solid #d9d9d9',
                      }}
                    />
                    <span>{preset.label}</span>
                  </Space>
                </Radio>
              </Col>
            ))}
            <Col span={8}>
              <Radio value="custom">Custom</Radio>
            </Col>
          </Row>
        </Radio.Group>
      </div>

      <Divider />

      <div>
        <Title level={5}>Custom Colors</Title>
        {isDarkMode && (
          <Alert
            message="Dark Mode Active"
            description="Background and Text colors are automatically handled by Ant Design's dark algorithm. Custom values for these colors mainly apply to light mode."
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {Object.entries(colorLabels).map(([key, label]) => {
            const isAutoHandled = isDarkMode && (key === 'background' || key === 'text')
            return (
              <Row key={key} align="middle" gutter={16}>
                <Col span={6}>
                  <Text strong>
                    {label}
                    {isAutoHandled && (
                      <Text type="secondary" style={{ fontSize: 12, display: 'block', fontWeight: 'normal' }}>
                        (auto in dark)
                      </Text>
                    )}
                  </Text>
                </Col>
                <Col span={18}>
                  <ColorPicker
                    value={customColors[key as keyof ThemeConfig['colors']]}
                    onChange={(color) =>
                      handleCustomColorChange(key as keyof ThemeConfig['colors'], color)
                    }
                    showText
                    format="hex"
                    disabled={isAutoHandled}
                  />
                </Col>
              </Row>
            )
          })}
        </Space>
      </div>
    </Space>
  )

  const renderSpacingTab = () => (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div>
        <Title level={5}>Padding</Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {(['padding', 'paddingLG', 'paddingMD', 'paddingSM', 'paddingXS', 'paddingXXS'] as const).map((key) => (
            <Row key={key} align="middle" gutter={16}>
              <Col span={8}>
                <Text>{key.replace('padding', 'Padding').replace(/([A-Z])/g, ' $1').trim()}</Text>
              </Col>
              <Col span={16}>
                <InputNumber
                  value={customSpacing[key]}
                  onChange={(value) => handleSpacingChange(key, value)}
                  min={0}
                  max={100}
                  addonAfter="px"
                  style={{ width: '100%' }}
                />
              </Col>
            </Row>
          ))}
        </Space>
      </div>
      <Divider />
      <div>
        <Title level={5}>Margin</Title>
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          {(['margin', 'marginLG', 'marginMD', 'marginSM', 'marginXS', 'marginXXS'] as const).map((key) => (
            <Row key={key} align="middle" gutter={16}>
              <Col span={8}>
                <Text>{key.replace('margin', 'Margin').replace(/([A-Z])/g, ' $1').trim()}</Text>
              </Col>
              <Col span={16}>
                <InputNumber
                  value={customSpacing[key]}
                  onChange={(value) => handleSpacingChange(key, value)}
                  min={0}
                  max={100}
                  addonAfter="px"
                  style={{ width: '100%' }}
                />
              </Col>
            </Row>
          ))}
        </Space>
      </div>
    </Space>
  )

  const renderBorderRadiusTab = () => (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {(['borderRadius', 'borderRadiusLG', 'borderRadiusSM', 'borderRadiusXS'] as const).map((key) => (
        <Row key={key} align="middle" gutter={16}>
          <Col span={8}>
            <Text>{key.replace('borderRadius', 'Radius').replace(/([A-Z])/g, ' $1').trim()}</Text>
          </Col>
          <Col span={16}>
            <InputNumber
              value={customBorderRadius[key]}
              onChange={(value) => handleBorderRadiusChange(key, value)}
              min={0}
              max={50}
              addonAfter="px"
              style={{ width: '100%' }}
            />
          </Col>
        </Row>
      ))}
    </Space>
  )

  const renderTypographyTab = () => (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {(['fontSize', 'fontSizeLG', 'fontSizeSM', 'fontSizeXL'] as const).map((key) => (
        <Row key={key} align="middle" gutter={16}>
          <Col span={8}>
            <Text>{key.replace('fontSize', 'Font Size').replace(/([A-Z])/g, ' $1').trim()}</Text>
          </Col>
          <Col span={16}>
            <InputNumber
              value={customTypography[key]}
              onChange={(value) => handleTypographyChange(key, value)}
              min={8}
              max={48}
              addonAfter="px"
              style={{ width: '100%' }}
            />
          </Col>
        </Row>
      ))}
      <Row align="middle" gutter={16}>
        <Col span={8}>
          <Text>Line Height</Text>
        </Col>
        <Col span={16}>
          <InputNumber
            value={customTypography.lineHeight}
            onChange={(value) => handleTypographyChange('lineHeight', value)}
            min={1}
            max={3}
            step={0.1}
            style={{ width: '100%' }}
          />
        </Col>
      </Row>
    </Space>
  )

  return (
    <Modal
      title="Theme Configuration"
      open={open}
      onCancel={onClose}
      footer={[
        <Button key="reset" icon={<ReloadOutlined />} onClick={handleReset}>
          Reset to Default
        </Button>,
        <Button key="close" type="primary" onClick={onClose}>
          Close
        </Button>,
      ]}
      width={700}
      destroyOnClose
    >
      <Tabs
        items={[
          {
            key: 'colors',
            label: 'Colors',
            children: renderColorsTab(),
          },
          {
            key: 'spacing',
            label: 'Spacing',
            children: renderSpacingTab(),
          },
          {
            key: 'borderRadius',
            label: 'Border Radius',
            children: renderBorderRadiusTab(),
          },
          {
            key: 'typography',
            label: 'Typography',
            children: renderTypographyTab(),
          },
        ]}
      />
    </Modal>
  )
}

export default ThemeConfigDialog

