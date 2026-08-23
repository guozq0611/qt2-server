import React from 'react';
import { RouteProps } from 'react-router-dom';
import DefaultHeaderTemplate from '../templates/layouts/Headers/DefaultHeader.template';
import { authPages } from '../config/pages.config';

const headerRoutes: RouteProps[] = [
	{ path: authPages.loginPage.to, element: null },
	{ path: '*', element: <DefaultHeaderTemplate /> },
];

export default headerRoutes;
