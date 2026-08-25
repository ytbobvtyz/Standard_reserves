import { Layout as AntLayout, Menu, Typography, Button, Space } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  CarOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/auth'

const { Header, Sider, Content } = AntLayout

export function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)

  const path = location.pathname
  const selectedKey = path.startsWith('/requests/create')
    ? '/requests/create'
    : path.startsWith('/requests')
      ? '/requests/my'
      : path.startsWith('/approvals')
        ? path
        : path.startsWith('/logistics')
          ? path
          : path.startsWith('/references/products')
            ? '/references/products'
            : path.startsWith('/references/objects')
              ? '/references/objects'
              : path.startsWith('/references')
                ? path
                : path.startsWith('/admin')
                  ? path
                  : path

  const canCreate = user?.role === 'commercial' || user?.role === 'logistics'
  const showPP = user?.role === 'pp'
  const showEconomy = user?.role === 'economist'
  const showAdmin = user?.role === 'logistics'

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: 'Дашборд' },
    { key: '/requests/my', icon: <FileTextOutlined />, label: 'Запросы' },
    ...(canCreate
      ? [
          {
            key: '/requests/create',
            icon: <FileTextOutlined />,
            label: 'Создать запрос',
          },
        ]
      : []),
    ...(showPP
      ? [
          {
            key: '/approvals/pp',
            icon: <CheckSquareOutlined />,
            label: 'Согласование ПП',
          },
        ]
      : []),
    ...(showEconomy
      ? [
          {
            key: '/approvals/economy',
            icon: <CheckSquareOutlined />,
            label: 'Согласование экономиста',
          },
        ]
      : []),
    { key: '/normatives', icon: <DatabaseOutlined />, label: 'Нормативы' },
    {
      key: '/logistics/dashboard',
      icon: <CarOutlined />,
      label: 'Логистика',
    },
    {
      key: '/logistics/one-time',
      icon: <CarOutlined />,
      label: 'Разовые перемещения',
    },
    {
      key: '/references/products',
      icon: <DatabaseOutlined />,
      label: 'Продукты',
    },
    {
      key: '/references/objects',
      icon: <DatabaseOutlined />,
      label: 'Объекты',
    },
    ...(showAdmin
      ? [
          {
            key: 'admin',
            icon: <TeamOutlined />,
            label: 'Администрирование',
            children: [
              { key: '/admin/users', label: 'Пользователи' },
              { key: '/admin/departments', label: 'Подразделения' },
            ],
          },
        ]
      : []),
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={64}>
        <div
          style={{
            color: '#fff',
            padding: '16px',
            fontWeight: 600,
            fontSize: 16,
          }}
        >
          Standart Reserve
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={showAdmin ? ['admin'] : []}
          onClick={({ key }) => {
            if (key.startsWith('/')) {
              navigate(key)
            }
          }}
          items={menuItems}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            padding: '0 24px',
          }}
        >
          <Space>
            <Typography.Text>{user?.full_name ?? 'Гость'}</Typography.Text>
            <Button
              icon={<LogoutOutlined />}
              onClick={async () => {
                await logout()
                navigate('/login')
              }}
            >
              Выйти
            </Button>
          </Space>
        </Header>
        <Content style={{ margin: 24, background: '#fff', padding: 24 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
