import React from 'react';
import { CheckCircle2, Clock, AlertTriangle, XCircle } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const normStatus = (status || 'running').toLowerCase();

  let className = 'status-pill running';
  let icon = <Clock size={14} />;

  if (normStatus === 'arrived') {
    className = 'status-pill arrived';
    icon = <CheckCircle2 size={14} />;
  } else if (normStatus === 'cancelled' || normStatus === 'canceled') {
    className = 'status-pill cancelled';
    icon = <XCircle size={14} />;
  } else if (normStatus.includes('delay')) {
    className = 'status-pill moderate';
    icon = <AlertTriangle size={14} />;
  }

  return (
    <span className={className}>
      {icon}
      <span>{status || 'Running'}</span>
    </span>
  );
};
