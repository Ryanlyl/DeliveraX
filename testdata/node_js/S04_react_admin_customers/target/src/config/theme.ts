import { MappingAlgorithm, theme } from 'antd'

/**
 * Theme color configuration
 */
export interface ThemeColors {
  /** Primary color */
  primary: string
  /** Secondary color */
  secondary: string
  /** Success color */
  success: string
  /** Warning color */
  warning: string
  /** Error color */
  error: string
  /** Info color */
  info: string
  /** Background color (mainly for light mode, dark mode uses Ant Design's darkAlgorithm) */
  background: string
  /** Text color (mainly for light mode, dark mode uses Ant Design's darkAlgorithm) */
  text: string
}

/**
 * Spacing configuration (padding and margin)
 */
export interface SpacingConfig {
  /** Base padding */
  padding: number
  /** Large padding */
  paddingLG: number
  /** Medium padding */
  paddingMD: number
  /** Small padding */
  paddingSM: number
  /** Extra small padding */
  paddingXS: number
  /** Extra extra small padding */
  paddingXXS: number
  /** Base margin */
  margin: number
  /** Large margin */
  marginLG: number
  /** Medium margin */
  marginMD: number
  /** Small margin */
  marginSM: number
  /** Extra small margin */
  marginXS: number
  /** Extra extra small margin */
  marginXXS: number
}

/**
 * Border radius configuration
 */
export interface BorderRadiusConfig {
  /** Base border radius */
  borderRadius: number
  /** Large border radius */
  borderRadiusLG: number
  /** Small border radius */
  borderRadiusSM: number
  /** Extra small border radius */
  borderRadiusXS: number
}

/**
 * Typography configuration
 */
export interface TypographyConfig {
  /** Base font size */
  fontSize: number
  /** Large font size */
  fontSizeLG: number
  /** Small font size */
  fontSizeSM: number
  /** Extra large font size */
  fontSizeXL: number
  /** Line height */
  lineHeight: number
}

/**
 * Theme configuration
 */
export interface ThemeConfig {
  /** Color configuration */
  colors: ThemeColors
  /** Spacing configuration */
  spacing: SpacingConfig
  /** Border radius configuration */
  borderRadius: BorderRadiusConfig
  /** Typography configuration */
  typography: TypographyConfig
  /** Ant Design algorithm array */
  algorithm: MappingAlgorithm[]
  /** Algorithm string array (for persistence) */
  _algorithm: string[]
}

/**
 * Preset theme name
 */
export type PresetThemeName = 'blue' | 'green' | 'purple' | 'orange' | 'teal' | 'red' | 'cyan'

/**
 * Preset theme configuration
 */
export interface PresetTheme {
  name: PresetThemeName
  label: string
  colors: ThemeColors
  spacing?: Partial<SpacingConfig>
  borderRadius?: Partial<BorderRadiusConfig>
  typography?: Partial<TypographyConfig>
}

/**
 * Algorithm mapping
 */
export const algorithmMap: Record<string, MappingAlgorithm> = {
  default: theme.defaultAlgorithm,
  dark: theme.darkAlgorithm,
  compact: theme.compactAlgorithm,
}

/**
 * Validate color format (hex format)
 */
export function isValidColor(color: string): boolean {
  if (!color) return false
  const hexPattern = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/
  return hexPattern.test(color)
}

/**
 * Convert color to rgba format
 */
export function toRgba(color: string, alpha: number): string {
  if (!color) return `rgba(0, 0, 0, ${alpha})`
  
  if (color.startsWith('rgb')) {
    return color.replace('rgb', 'rgba').replace(')', `, ${alpha})`)
  }
  
  let hex = color.replace('#', '')
  if (hex.length === 3) {
    hex = hex.split('').map((char) => char + char).join('')
  }
  
  const bigint = parseInt(hex, 16)
  const r = (bigint >> 16) & 255
  const g = (bigint >> 8) & 255
  const b = bigint & 255
  
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

/**
 * Create default spacing configuration
 */
export function createDefaultSpacingConfig(): SpacingConfig {
  return {
    padding: 16,
    paddingLG: 24,
    paddingMD: 16,
    paddingSM: 12,
    paddingXS: 8,
    paddingXXS: 4,
    margin: 16,
    marginLG: 24,
    marginMD: 16,
    marginSM: 12,
    marginXS: 8,
    marginXXS: 4,
  }
}

/**
 * Create default border radius configuration
 */
export function createDefaultBorderRadiusConfig(): BorderRadiusConfig {
  return {
    borderRadius: 6,
    borderRadiusLG: 8,
    borderRadiusSM: 4,
    borderRadiusXS: 2,
  }
}

/**
 * Create default typography configuration
 */
export function createDefaultTypographyConfig(): TypographyConfig {
  return {
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeSM: 12,
    fontSizeXL: 20,
    lineHeight: 1.5715,
  }
}

/**
 * Create default theme configuration
 */
export function createDefaultThemeConfig(): ThemeConfig {
  return {
    colors: {
      primary: '#1890ff',
      secondary: '#722ed1',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
    spacing: createDefaultSpacingConfig(),
    borderRadius: createDefaultBorderRadiusConfig(),
    typography: createDefaultTypographyConfig(),
    algorithm: [theme.defaultAlgorithm],
    _algorithm: ['default'],
  }
}

/**
 * Build algorithm array from algorithm string array
 */
export function buildAlgorithmArray(algorithmStrings: string[]): MappingAlgorithm[] {
  return algorithmStrings.map((item) => algorithmMap[item] || theme.defaultAlgorithm)
}

