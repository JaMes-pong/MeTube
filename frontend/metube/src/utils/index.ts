import type { ProgressData } from '@/types';

export const API_BASE_URL = 'http://localhost:8000';

export const formatDuration = (seconds?: number): string => {
	if (!seconds) return '0:00';
	const mins = Math.floor(seconds / 60);
	const secs = seconds % 60;
	return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const formatBytes = (bytes?: number): string => {
	if (!bytes) return '0 B';
	const k = 1024;
	const sizes = ['B', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const parseProgress = (data: string): ProgressData => {
	const jsonString = data
		.replace(/'/g, '"')
		.replace(/True/g, 'true')
		.replace(/False/g, 'false')
		.replace(/None/g, 'null');

	return JSON.parse(jsonString);
};

export const downloadFileHandler = (jobId: string, videoName: string = 'video'): void => {
	const downloadUrl = `${API_BASE_URL}/api/download/file/${jobId}`;
	const link = document.createElement('a');
	link.href = downloadUrl;
	link.download = videoName;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
};
