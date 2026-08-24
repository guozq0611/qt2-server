import React, { useEffect, useState } from 'react';
import dayjs from 'dayjs';
import Footer, { FooterLeft, FooterRight } from '../../../components/layouts/Footer/Footer';
import api from '../../../api';

const DefaultFooterTemplate = () => {
	const [brand, setBrand] = useState('Alan Intelligent Technology');

	useEffect(() => {
		const fetchBrand = async () => {
			try {
				const result = await api.getConfig();
				const b = (result as any)?.app?.brand;
				if (b) setBrand(b);
			} catch {
				// 使用默认值
			}
		};
		fetchBrand();
	}, []);

	return (
		<Footer>
			<FooterLeft className='text-zinc-500'>
				<div>Copyright © {dayjs().format('YYYY')}</div>
			</FooterLeft>
			<FooterRight className='text-zinc-500'>
				<span>
					<b>{brand}</b>
				</span>
			</FooterRight>
		</Footer>
	);
};

export default DefaultFooterTemplate;
