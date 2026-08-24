import React, { lazy } from 'react';
import { RouteProps } from 'react-router-dom';
import { appPages, authPages } from '../config/pages.config';
import NotFoundPage from '../pages/NotFound.page';
import LoginPage from '../pages/Login.page';

// qt2-server 页面
const DashboardPage = lazy(() => import('../pages/DashboardPage/Dashboard.page'));
const TickSnapshotPage = lazy(() => import('../pages/TickSnapshotPage/TickSnapshot.page'));
const InstrumentsPage = lazy(() => import('../pages/InstrumentsPage/Instruments.page'));
const FilesPage = lazy(() => import('../pages/FilesPage/Files.page'));
const ConfigPage = lazy(() => import('../pages/ConfigPage/Config.page'));

const contentRoutes: RouteProps[] = [
	{ path: authPages.loginPage.to, element: <LoginPage /> },
	{ path: appPages.dashboardPage.to, element: <DashboardPage /> },
	{ path: appPages.tickSnapshotPage.to, element: <TickSnapshotPage /> },
	{ path: appPages.instrumentsPage.to, element: <InstrumentsPage /> },
	{ path: appPages.filesPage.to, element: <FilesPage /> },
	{ path: appPages.configPage.to, element: <ConfigPage /> },
	{ path: '*', element: <NotFoundPage /> },
];

export default contentRoutes;
