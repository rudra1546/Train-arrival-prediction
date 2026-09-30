import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, XCircle, Radio } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normStatus = (status || 'running').toLowerCase();

  let className = 'status-pill running';
  let icon = <Radio size={13} className="pill-pulse-dot" />;

  if (normStatus === 'arrived') {
    className = 'status-pill arrived';
    icon = <CheckCircle2 size={13} />;
  } else if (normStatus === 'cancelled' || normStatus === 'canceled') {
    className = 'status-pill cancelled';
    icon = <XCircle size={13} />;
  } else if (normStatus.includes('delay') || normStatus.includes('late')) {
    className = 'status-pill delayed';
    icon = <AlertTriangle size={13} />;
  } else {
    className = 'status-pill running';
    icon = <Clock size={13} />;
  }

  return (
    <span className={className}>
      {icon}
      <span className="status-pill-text">{status || 'Running'}</span>
    </span>
  );
};
