import type { DownloadRequest } from '@/types';
import { API_BASE_URL } from '@/utils';

const fetchVideoInfo = async (url: string): Promise<Response> => {
	const response = await fetch(`${API_BASE_URL}/api/get-video-info`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			url,
			format: 'best',
			output_format: 'original',
		} as DownloadRequest),
	});

	return response;
};

const downloadVideo = async (opts: DownloadRequest): Promise<Response> => {
	const response = await fetch(`${API_BASE_URL}/api/download/start`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(opts),
	});

	return response;
};

const jobCleanup = async (jobId: string): Promise<void> => {
	await fetch(`${API_BASE_URL}/api/download/${jobId}`, {
		method: 'DELETE',
	});
};

export { fetchVideoInfo, downloadVideo, jobCleanup };
