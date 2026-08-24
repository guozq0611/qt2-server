import React from 'react';
import dayjs from 'dayjs';
import Footer, { FooterLeft, FooterRight } from '../../../components/layouts/Footer/Footer';

const DefaultFooterTemplate = () => {
	return (
		<Footer>
			<FooterLeft className='text-zinc-500'>
				<div>Copyright © {dayjs().format('YYYY')}</div>
			</FooterLeft>
			<FooterRight className='text-zinc-500'>
				<span>
					<b>Alan Intelligent Technology</b>
				</span>
			</FooterRight>
		</Footer>
	);
};

export default DefaultFooterTemplate;
