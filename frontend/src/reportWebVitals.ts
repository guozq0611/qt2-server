const reportWebVitals = (onPerfEntry?: Performance) => {
	if (onPerfEntry && onPerfEntry instanceof Function) {
		// @ts-expect-error
		import('web-vitals').then(({ getCLS, getFID, getFCP, getLCP, getTTFB }) => {
			getCLS(onPerfEntry);
			getFID(onPerfEntry);
			getFCP(onPerfEntry);
			getLCP(onPerfEntry);
			getTTFB(onPerfEntry);
		});
	}
};

export default reportWebVitals;
