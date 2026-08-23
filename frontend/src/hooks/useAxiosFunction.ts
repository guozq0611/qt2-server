import { useEffect, useState } from 'react';
import axios, { AxiosHeaders, Method, RawAxiosRequestHeaders } from 'axios';

const BASE_URL = '';

const axiosInstanceDefault = axios.create({
	baseURL: BASE_URL,
	headers: { 'Content-Type': 'application/json' },
});

const useAxiosFunction = () => {
	const [response, setResponse] = useState([]);
	const [error, setError] = useState('');
	const [loading, setLoading] = useState(false);
	const [controller, setController] = useState();

	const axiosFetch = async (configObj: {
		axiosInstance: { baseURL: string; headers: RawAxiosRequestHeaders | AxiosHeaders };
		method: Method;
		url: string;
		requestConfig?: object;
	}) => {
		const { axiosInstance = axiosInstanceDefault, method, url, requestConfig = {} } = configObj;

		try {
			setLoading(true);
			const ctrl = new AbortController();

			// @ts-expect-error
			setController(ctrl);

			// @ts-expect-error
			const res = await axiosInstance[method.toLowerCase()](url, {
				...requestConfig,
				signal: ctrl.signal,
			});
			// console.log(res);

			setResponse(res.data);
		} catch (err) {
			// console.log(err.message);

			// @ts-expect-error
			setError(err.message);
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		// console.log(controller);

		// useEffect cleanup function

		// @ts-expect-error

		return () => controller && controller.abort();
	}, [controller]);

	return [response, error, loading, axiosFetch];
};

export default useAxiosFunction;
