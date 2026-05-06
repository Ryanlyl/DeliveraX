import { PresetTheme } from './theme'

/**
 * Preset theme collection
 */
export const themePresets: Record<string, PresetTheme> = {
  blue: {
    name: 'blue',
    label: 'Blue',
    colors: {
      primary: '#1890ff',
      secondary: '#096dd9',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
  green: {
    name: 'green',
    label: 'Green',
    colors: {
      primary: '#52c41a',
      secondary: '#389e0d',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
  purple: {
    name: 'purple',
    label: 'Purple',
    colors: {
      primary: '#722ed1',
      secondary: '#531dab',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
  orange: {
    name: 'orange',
    label: 'Orange',
    colors: {
      primary: '#fa8c16',
      secondary: '#d46b08',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
  teal: {
    name: 'teal',
    label: 'Teal',
    colors: {
      primary: '#03dac6',
      secondary: '#018786',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
  red: {
    name: 'red',
    label: 'Red',
    colors: {
      primary: '#ff4d4f',
      secondary: '#cf1322',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
  cyan: {
    name: 'cyan',
    label: 'Cyan',
    colors: {
      primary: '#03dac6',
      secondary: '#018786',
      success: '#52c41a',
      warning: '#faad14',
      error: '#ff4d4f',
      info: '#1890ff',
      background: '#ffffff',
      text: '#000000',
    },
  },
}

/**
 * Get preset theme by name
 */
export function getPresetTheme(name: string): PresetTheme | undefined {
  return themePresets[name]
}

/**
 * Get all preset themes list
 */
export function getAllPresetThemes(): PresetTheme[] {
  return Object.values(themePresets)
}

