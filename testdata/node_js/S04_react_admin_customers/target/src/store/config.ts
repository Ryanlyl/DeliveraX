import { uniq } from 'lodash-es'
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ThemeConfig, PresetThemeName, SpacingConfig, BorderRadiusConfig, TypographyConfig } from '../config/theme'
import { createDefaultThemeConfig, buildAlgorithmArray, createDefaultSpacingConfig, createDefaultBorderRadiusConfig, createDefaultTypographyConfig } from '../config/theme'
import { getPresetTheme } from '../config/theme-presets'

type ConfigState = {
  themeConfig: ThemeConfig
  /** Current preset theme name */
  currentPresetTheme?: PresetThemeName
  themeOptions: { label: string, value: string }[]
}

type Actions = {
  setAlgorithm: (v: string) => void
  setCompactAlgorithm: (v: string) => void
  /** Switch preset theme */
  setTheme: (presetName: PresetThemeName) => void
  /** Customize a single color */
  setCustomColor: (colorKey: keyof ThemeConfig['colors'], color: string) => void
  /** Set spacing configuration */
  setSpacing: (spacing: Partial<SpacingConfig>) => void
  /** Set border radius configuration */
  setBorderRadius: (borderRadius: Partial<BorderRadiusConfig>) => void
  /** Set typography configuration */
  setTypography: (typography: Partial<TypographyConfig>) => void
  /** Reset theme to default configuration */
  resetTheme: () => void
  /** Get primary color (backward compatibility) */
  getPrimaryColor: () => string
}

// Create default theme config (use orange as default, maintain backward compatibility)
const defaultThemeConfig = createDefaultThemeConfig()
// Use orange theme colors as default
const orangePreset = getPresetTheme('orange')
if (orangePreset) {
  defaultThemeConfig.colors = { ...orangePreset.colors }
}

const useConfigStore = create<ConfigState & Actions>()(
  persist(
    (set, get) => ({
      themeConfig: defaultThemeConfig,
      currentPresetTheme: 'orange',
      themeOptions: [
        { label: 'Light', value: 'default' },
        { label: 'Dark', value: 'dark' },
        { label: 'Compact', value: 'compact' },
      ],
      setAlgorithm: (v: string) => {
        set((state) => {
          const includesCompact = state.themeConfig._algorithm.includes('compact')
          const _algorithm = includesCompact ? [v, 'compact'] : [v]

          return {
            themeConfig: {
              ...state.themeConfig,
              _algorithm,
              algorithm: buildAlgorithmArray(_algorithm),
            }
          }
        })
      },
      setCompactAlgorithm: (v: string) => {
        set((state) => {
          const withoutCompact = state.themeConfig._algorithm.filter((item) => item !== 'compact')
          const _algorithm = uniq(v ? [...withoutCompact, 'compact'] : withoutCompact)

          return {
            themeConfig: {
              ...state.themeConfig,
              _algorithm,
              algorithm: buildAlgorithmArray(_algorithm),
            }
          }
        })
      },
      setTheme: (presetName: PresetThemeName) => {
        const preset = getPresetTheme(presetName)
        if (preset) {
          set((state) => ({
            currentPresetTheme: presetName,
            themeConfig: {
              ...state.themeConfig,
              colors: { ...preset.colors },
            }
          }))
        }
      },
      setCustomColor: (colorKey: keyof ThemeConfig['colors'], color: string) => {
        set((state) => ({
          currentPresetTheme: undefined, // Clear preset theme after customizing colors
          themeConfig: {
            ...state.themeConfig,
            colors: {
              ...state.themeConfig.colors,
              [colorKey]: color,
            }
          }
        }))
      },
      setSpacing: (spacing: Partial<SpacingConfig>) => {
        set((state) => ({
          themeConfig: {
            ...state.themeConfig,
            spacing: {
              ...state.themeConfig.spacing,
              ...spacing,
            }
          }
        }))
      },
      setBorderRadius: (borderRadius: Partial<BorderRadiusConfig>) => {
        set((state) => ({
          themeConfig: {
            ...state.themeConfig,
            borderRadius: {
              ...state.themeConfig.borderRadius,
              ...borderRadius,
            }
          }
        }))
      },
      setTypography: (typography: Partial<TypographyConfig>) => {
        set((state) => ({
          themeConfig: {
            ...state.themeConfig,
            typography: {
              ...state.themeConfig.typography,
              ...typography,
            }
          }
        }))
      },
      resetTheme: () => {
        // Reset to orange theme and default configurations
        const preset = getPresetTheme('orange')
        if (preset) {
          set((state) => ({
            currentPresetTheme: 'orange',
            themeConfig: {
              ...state.themeConfig,
              colors: { ...preset.colors },
              spacing: createDefaultSpacingConfig(),
              borderRadius: createDefaultBorderRadiusConfig(),
              typography: createDefaultTypographyConfig(),
            }
          }))
        }
      },
      getPrimaryColor: () => {
        return get().themeConfig.colors.primary
      },
    }),
    {
      name: 'config-storage',
      onRehydrateStorage: () => (state) => {
        // Rebuild algorithm array from _algorithm strings after rehydration
        if (state) {
          // Handle old version data migration
          const oldConfig = state.themeConfig as ThemeConfig & { primaryColor?: string; spacing?: SpacingConfig; borderRadius?: BorderRadiusConfig; typography?: TypographyConfig }
          
          // Migrate from old color structure
          if ('primaryColor' in oldConfig && oldConfig.primaryColor && !oldConfig.colors) {
            state.themeConfig = {
              colors: {
                primary: oldConfig.primaryColor || '#03dac6',
                secondary: '#018786',
                success: '#52c41a',
                warning: '#faad14',
                error: '#ff4d4f',
                info: '#1890ff',
                background: '#ffffff',
                text: '#000000',
              },
              spacing: oldConfig.spacing || createDefaultSpacingConfig(),
              borderRadius: oldConfig.borderRadius || createDefaultBorderRadiusConfig(),
              typography: oldConfig.typography || createDefaultTypographyConfig(),
              _algorithm: oldConfig._algorithm || ['default'],
              algorithm: buildAlgorithmArray(oldConfig._algorithm || ['default']),
            }
          } else {
            // Ensure new fields exist for existing configs
            if (!state.themeConfig.spacing) {
              state.themeConfig.spacing = createDefaultSpacingConfig()
            }
            if (!state.themeConfig.borderRadius) {
              state.themeConfig.borderRadius = createDefaultBorderRadiusConfig()
            }
            if (!state.themeConfig.typography) {
              state.themeConfig.typography = createDefaultTypographyConfig()
            }
            state.themeConfig.algorithm = buildAlgorithmArray(state.themeConfig._algorithm)
          }
        }
      },
    }
  )
)

export default useConfigStore
