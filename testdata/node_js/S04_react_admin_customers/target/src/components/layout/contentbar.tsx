import React, { useEffect, useState } from 'react';

import { Outlet } from 'react-router-dom';
import { Card } from 'antd';

// Custom hook for responsive breakpoints
const useResponsive = () => {
  const [isMobile, setIsMobile] = useState(false)
  const [isTablet, setIsTablet] = useState(false)

  useEffect(() => {
    const checkSize = () => {
      setIsMobile(window.innerWidth <= 768)
      setIsTablet(window.innerWidth > 768 && window.innerWidth <= 1024)
    }
    
    checkSize()
    window.addEventListener('resize', checkSize)
    return () => window.removeEventListener('resize', checkSize)
  }, [])

  return { isMobile, isTablet }
}

const PageContent: React.FC = () => {
  const { isMobile, isTablet } = useResponsive()

  return (
    <div style={{ 
      padding: isMobile ? "12px" : isTablet ? "16px" : "20px", 
      minHeight: "calc(100vh - 200px)",
    }}>
      <Card style={{ 
        minHeight: "100%",
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      }}>
        <Outlet />
      </Card>
    </div>
  );
};

export default PageContent;
