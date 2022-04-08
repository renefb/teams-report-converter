import datetime
import numpy as np
import pandas as pd
import pytz


class TeamsAttendeeEngagementReportHandler:
    
    def __init__(self, report_content, event_start, event_end, local_tz='GMT'):
        self.__report_content = report_content
        # self.__report_tz = pytz.timezone('GMT')
        self.__event_start = pd.Timestamp(event_start, tz=local_tz).astimezone(pytz.timezone('GMT'))
        self.__event_end = pd.Timestamp(event_end, tz=local_tz).astimezone(pytz.timezone('GMT'))
        self.__tz_localizer = pytz.timezone(local_tz)
                
        self.__df = self.__load_csv()
        self.__joined_df = self.__filter_by_action('Joined')
        self.__left_df = self.__filter_by_action('Left')
        self.__sessions = self.__pair_sessions()
        self.__participants = self.__calculate_frequency()
        
        self.__print_summary()
        
        ## apagar?
        self.df = self.__df
        self.joined = self.__joined_df
        self.left = self.__left_df
        self.sessions = self.__sessions
        self.start = self.__event_start
        self.end = self.__event_end
        self.parts = self.__participants
        
    
    def __load_csv(self):
        df = pd.read_csv(self.__report_content, parse_dates=['UTC Event Timestamp'])
        df['UTC Event Timestamp'] = df['UTC Event Timestamp'].apply(lambda x: pytz.timezone('GMT').localize(x))
        df = df.sort_values(by=['UTC Event Timestamp'])
        return df
        
        
    
    def __filter_by_action(self, action):
        action_timestamp_column = f'UTC {action} Timestamp'
        action_sess = self.__df.query('Action==@action').rename(columns={'UTC Event Timestamp': action_timestamp_column})
        keep_param = 'first' if action=="Joined" else 'last'
        action_sess = action_sess.drop_duplicates(subset='Session Id', keep=keep_param)
        action_sess = action_sess.set_index('Session Id')
        target_cols = ['Participant Id', 'Full Name', 'UserAgent', 'Role', action_timestamp_column]
        return action_sess[target_cols]
 
    
    def __print_summary(self):
        width = 50
        summary = {
            # 'header': {
            #     'S U M M A R Y': '',
            # },
            'start_end': {
                'Informed event start': self.__event_start,
                'Informed event end': self.__event_end
            },
            'records': {
                'Rows': str(self.__df.shape[0])
            },
            'join': {
                'Joined rows': self.__joined_df.shape[0],
                ' - First at': self.__joined_df['UTC Joined Timestamp'].min(),
                ' - Last at': self.__joined_df['UTC Joined Timestamp'].max(),
            },
            'left': {
                'Left rows': self.__left_df.shape[0],
                ' - First at': self.__left_df['UTC Left Timestamp'].min(),
                ' - Last at': self.__left_df['UTC Left Timestamp'].max()
            },
            'sessions': {
                'Unique sessions': len(self.__df['Session Id'].unique()),
                ' - Left before event start': (self.__sessions['Session Validation']=='Left early').sum(),
                ' - Joined after event end': (self.__sessions['Session Validation']=='Joined late').sum(),
                ' - Without Participant Id': self.__sessions['Participant Id'].isnull().sum(),
            },
            'participants': {
                'Unique participants': len(self.__sessions['Participant Id'].unique())
            }
        }

        print('S U M M A R Y'.center(width))
        print('-'*width)        
        for section_names, section_values in summary.items():
            for k, v, in section_values.items():
                len_k = len(k)
                print(k, str(v).rjust(width - len_k - 1))
            print('-'*width)
        
    
        
    def __pair_sessions(self):
        paired_sess = pd.concat([self.__joined_df, self.__left_df['UTC Left Timestamp']], axis=1)
        
        is_join_late = paired_sess['UTC Joined Timestamp'].apply(lambda x: True if x >= self.__event_end else False)
        is_leaving_early = paired_sess['UTC Left Timestamp'].apply(lambda x: True if x <= self.__event_start else False)
        
        paired_sess['Session Validation'] = 'Valid'
        paired_sess.loc[is_join_late,'Session Validation'][is_join_late] = 'Joined late'
        paired_sess.loc[is_leaving_early, 'Session Validation'] = 'Left early'
        
        return paired_sess


    def __calculate_frequency(self):
        participants_sess = self.__sessions.copy()
        participants_sess = participants_sess[~participants_sess['Participant Id'].isnull()]
        participants_sess = participants_sess[participants_sess['Session Validation']=='Valid']
        
        participants_ids = participants_sess['Participant Id'].unique()
        participants_sess = participants_sess.set_index('Participant Id')

        target_columns = ['Full Name', 'Role', 'UTC Joined Timestamp', 'UTC Left Timestamp']
        participants_sess = participants_sess[target_columns]
        participants_sess['Session Duration'] = participants_sess['UTC Left Timestamp'] - participants_sess['UTC Joined Timestamp']
        
        freq = []

        for id in participants_ids:
            participant = {'Participant Id': id}
            participant_freq = participants_sess.loc[id]
            if type(participant_freq)==pd.Series:
                print('\tis a series')
                participant_freq = participant_freq.to_frame()

            fields_to_drop = ['UTC Joined Timestamp', 'UTC Left Timestamp']

            print(f'Participant {id} has {participant_freq.shape[0]} valid sessions')
            if participant_freq.shape[0]==1:
                print('\tsingle session')
                participant.update(participant_freq.drop(fields_to_drop).to_dict())
            else:
                print('\tmultiple sessions')
                participant = self.__merge_sessions(participant_freq)
                participant = participant.drop(fields_to_drop).to_dict()
            freq.append(participant)

        return pd.DataFrame(freq)
    

    def __merge_sessions(self, df):
        # ['Participant Id']['Full Name', 'Role', 'UTC Joined Timestamp', 'UTC Left Timestamp', 'Session Duration']
        print('\tentering into merge sessions:')
        print(df)
        session = df.iloc[0]
        print('\t', type(session))
        joined = session['UTC Joined Timestamp']
        left = session['UTC Left Timestamp']
        duration = session['Session Duration']
        duration_arr = []

        print('\tentering iterrows')
        for i, row in df.iloc[1:].iterrows():
            if row['UTC Joined Timestamp'] < left:
                if row['UTC Left Timestamp'] <= left:
                    pass
                else:
                    left = row['UTC Left Timestamp']
                    duration = left - joined
            else:
                duration_arr.append(duration)
                joined = row['UTC Joined Timestamp']
                left = row['UTC Left Timestamp']
                duration = left - joined
        print('\texiting iterrows\n----------------------------')

        duration_arr.append(duration)
        duration_sum = np.array(duration_arr).sum()
        session.loc['Session Duration'] = duration_sum

        return session


