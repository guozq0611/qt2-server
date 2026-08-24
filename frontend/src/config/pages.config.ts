/**
 * qt2-server 页面配置
 * 侧边栏导航和路由的统一配置源
 */
export const appPages = {
  dashboardPage: {
    id: 'dashboardPage',
    to: '/',
    text: '系统总览',
    icon: 'HeroRectangleGroup',
  },
  tickSnapshotPage: {
    id: 'tickSnapshotPage',
    to: '/ticks',
    text: '行情快照',
    icon: 'HeroChartBar',
  },
  instrumentsPage: {
    id: 'instrumentsPage',
    to: '/instruments',
    text: '合约列表',
    icon: 'HeroListBullet',
  },
  filesPage: {
    id: 'filesPage',
    to: '/files',
    text: '落盘文件',
    icon: 'HeroDocument',
  },
  configPage: {
    id: 'configPage',
    to: '/config',
    text: '配置查看',
    icon: 'HeroCog6Tooth',
  },
};

export const authPages = {
  loginPage: {
    id: 'loginPage',
    to: '/login',
    text: 'Login',
    icon: 'HeroUser',
  },
};

export const componentsPages = {};

export const examplePages = {};
