export interface VideoInfo {
	title: string;
	duration: number;
	thumbnail: string;
	uploader: string;
	formats: VideoFormat[];
}

export interface VideoFormat {
	format_id: string;
	resolution: string;
	ext: string;
	filesize: number;
	has_filesize: boolean;
}

export interface DownloadRequest {
	url: string;
	format: string;
	output_format: string;
}

export interface DownloadJob {
	job_id: string;
	status: string;
	message: string;
}

export interface ProgressData {
	status: 'starting' | 'downloading' | 'processing' | 'completed' | 'error' | 'waiting';
	percentage?: number;
	downloaded?: number;
	total?: number;
	speed?: number;
	eta?: number;
	filename?: string;
	message?: string;
	error_type?: string;
	timestamp?: string;
}

export interface ErrorResponse {
	detail: string;
}

export type FormatType = 'best' | '2160p' | '1440p' | '1080p' | '720p' | '480p' | '360p' | 'audio';
export type OutputFormat = 'original' | 'mp4' | 'webm';
