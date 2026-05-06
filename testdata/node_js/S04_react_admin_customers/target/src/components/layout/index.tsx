import React, { useState, useEffect } from 'react';

import { Layout, theme } from 'antd';
import PageSidebar from './sidebar';
import PageContent from './contentbar';
import PageBreadcrumb from './breadcrumb';
import Headerbar from './headerbar';

const { Footer } = Layout;

// Custom hook for responsive breakpoints
const useResponsive = () => {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkSize = () => {
      setIsMobile(window.innerWidth <= 768)
    }
    
    checkSize()
    window.addEventListener('resize', checkSize)
    return () => window.removeEventListener('resize', checkSize)
  }, [])

  return { isMobile }
}

const PageLayout: React.FC = () => {
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const { isMobile } = useResponsive()
  const [collapsed, setCollapsed] = useState(isMobile);
  const headerHeight = 64

  // Auto collapse on mobile
  useEffect(() => {
    if (isMobile) {
      setCollapsed(true)
    }
  }, [isMobile])

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Headerbar 
        colorBgContainer={colorBgContainer} 
        collapsed={collapsed}
        onCollapse={setCollapsed}
      />
      <Layout style={{ marginTop: headerHeight }}>
        <PageSidebar 
          height={`calc(100vh - ${headerHeight}px)`}
          collapsed={collapsed}
          onCollapse={setCollapsed}
        />
        <Layout style={{ 
          marginLeft: isMobile ? 0 : (collapsed ? 80 : 200),
          transition: 'margin-left 0.2s',
          minHeight: `calc(100vh - ${headerHeight}px)`,
        }}>
          <PageBreadcrumb />
          <PageContent></PageContent>
          <Footer style={{ textAlign: 'center', padding: '16px' }}>
            React Admin Dashboard ©{new Date().getFullYear()} Created by Yujian Xue
          </Footer>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default PageLayout;
