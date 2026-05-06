import React, { useEffect } from 'react';
import PageLayout from './components/layout';
import { ConfigProvider } from 'antd';
import useConfigStore from './store/config';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import useUserStore from './store/user';

const App: React.FC = () => {
  const themeConfig = useConfigStore(state => state.themeConfig)
  const navigate = useNavigate()
  const location = useLocation()
  const isAuthenticated = useUserStore(state => state.isAuthenticated)

  // Handle default route redirect
  useEffect(() => {
    if (location.pathname === '/') {
      if (isAuthenticated) {
        navigate('/dashboard', { replace: true })
      } else {
        navigate('/auth/login', { replace: true })
      }
    }
  }, [location.pathname, isAuthenticated, navigate])

  // Don't show layout for auth pages
  const isAuthPage = location.pathname.startsWith('/auth/')

  return (
    <ConfigProvider theme={{
      algorithm: themeConfig.algorithm,
      token: {
        // Colors
        // Note: colorBgContainer and colorText are handled automatically by Ant Design's darkAlgorithm
        // They will be automatically adjusted based on the algorithm (light/dark mode)
        colorPrimary: themeConfig.colors.primary,
        colorSuccess: themeConfig.colors.success,
        colorWarning: themeConfig.colors.warning,
        colorError: themeConfig.colors.error,
        colorInfo: themeConfig.colors.info,
        // Spacing - Padding
        padding: themeConfig.spacing.padding,
        paddingLG: themeConfig.spacing.paddingLG,
        paddingMD: themeConfig.spacing.paddingMD,
        paddingSM: themeConfig.spacing.paddingSM,
        paddingXS: themeConfig.spacing.paddingXS,
        paddingXXS: themeConfig.spacing.paddingXXS,
        // Spacing - Margin
        margin: themeConfig.spacing.margin,
        marginLG: themeConfig.spacing.marginLG,
        marginMD: themeConfig.spacing.marginMD,
        marginSM: themeConfig.spacing.marginSM,
        marginXS: themeConfig.spacing.marginXS,
        marginXXS: themeConfig.spacing.marginXXS,
        // Border Radius
        borderRadius: themeConfig.borderRadius.borderRadius,
        borderRadiusLG: themeConfig.borderRadius.borderRadiusLG,
        borderRadiusSM: themeConfig.borderRadius.borderRadiusSM,
        borderRadiusXS: themeConfig.borderRadius.borderRadiusXS,
        // Typography
        fontSize: themeConfig.typography.fontSize,
        fontSizeLG: themeConfig.typography.fontSizeLG,
        fontSizeSM: themeConfig.typography.fontSizeSM,
        fontSizeXL: themeConfig.typography.fontSizeXL,
        lineHeight: themeConfig.typography.lineHeight,
      }
    }}>
      {isAuthPage ? <Outlet /> : <PageLayout />}
    </ConfigProvider>
  )
};

export default App;
