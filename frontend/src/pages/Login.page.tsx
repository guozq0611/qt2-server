import React, { useState } from 'react';
import { useFormik } from 'formik';
import classNames from 'classnames';
import PageWrapper from '../components/layouts/PageWrapper/PageWrapper';
import Button from '../components/ui/Button';
import { useAuth } from '../context/authContext';
import Input from '../components/form/Input';
import LogoTemplate from '../templates/layouts/Logo/Logo.template';
import FieldWrap from '../components/form/FieldWrap';
import Icon from '../components/icon/Icon';
import Validation from '../components/form/Validation';

type TValues = {
	username: string;
	password: string;
};

const LoginPage = () => {
	const { onLogin } = useAuth();

	const [passwordShowStatus, setPasswordShowStatus] = useState<boolean>(false);

	const formik = useFormik({
		initialValues: {
			username: 'admin',
			password: '',
		},
		validate: (values: TValues) => {
			const errors: Partial<TValues> = {};

			if (!values.username) {
				errors.username = 'Required';
			}

			if (!values.password) {
				errors.password = 'Required';
			}

			return errors;
		},
		onSubmit: (values: TValues, { setFieldError }) => {
			onLogin(values.username, values.password)
				.then(() => {})
				.catch((e: Error) => {
					if (e.cause === 'username') {
						setFieldError('username', e.message);
						setFieldError('password', e.message);
					}
					if (e.cause === 'password') setFieldError('password', e.message);
				});
		},
	});

	return (
		<PageWrapper isProtectedRoute={false} className='bg-white dark:bg-inherit' name='Sign In'>
			<div className='container mx-auto flex h-full items-center justify-center'>
				<div className='flex max-w-sm flex-col gap-8'>
					<div>
						<LogoTemplate className='h-12' />
					</div>
					<div>
						<span className='text-4xl font-semibold'>qt2-server</span>
					</div>
					<form className='flex flex-col gap-4' noValidate>
						<div
							className={classNames({
								'mb-2': !formik.isValid,
							})}>
							<Validation
								isValid={formik.isValid}
								isTouched={formik.touched.username}
								invalidFeedback={formik.errors.username}
								validFeedback='Good'>
								<FieldWrap
									firstSuffix={<Icon icon='HeroEnvelope' className='mx-2' />}>
									<Input
										dimension='lg'
										id='username'
										autoComplete='username'
										name='username'
										placeholder='Email or username'
										value={formik.values.username}
										onChange={formik.handleChange}
										onBlur={formik.handleBlur}
									/>
								</FieldWrap>
							</Validation>
						</div>
						<div
							className={classNames({
								'mb-2': !formik.isValid,
							})}>
							<Validation
								isValid={formik.isValid}
								isTouched={formik.touched.password}
								invalidFeedback={formik.errors.password}
								validFeedback='Good'>
								<FieldWrap
									firstSuffix={<Icon icon='HeroKey' className='mx-2' />}
									lastSuffix={
										<Icon
											className='mx-2 cursor-pointer'
											icon={passwordShowStatus ? 'HeroEyeSlash' : 'HeroEye'}
											onClick={() => {
												setPasswordShowStatus(!passwordShowStatus);
											}}
										/>
									}>
									<Input
										dimension='lg'
										type={passwordShowStatus ? 'text' : 'password'}
										autoComplete='current-password'
										id='password'
										name='password'
										placeholder='Password'
										value={formik.values.password}
										onChange={formik.handleChange}
										onBlur={formik.handleBlur}
									/>
								</FieldWrap>
							</Validation>
						</div>
						<div>
							<Button
								size='lg'
								variant='solid'
								className='w-full font-semibold'
								onClick={() => formik.handleSubmit()}>
								Sign in
							</Button>
						</div>
					</form>
				</div>
			</div>
		</PageWrapper>
	);
};

export default LoginPage;
