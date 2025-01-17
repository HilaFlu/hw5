import json
import pandas as pd
import numpy as np
import pathlib
from typing import Union
from typing import Tuple


class QuestionnaireAnalysis:
    """
    Reads and analyzes data generated by the questionnaire experiment.
    Should be able to accept strings and pathlib.Path objects.
    """

    def __init__(self, data_fname: Union[pathlib.Path, str]):
        if pathlib.Path(data_fname).is_file():
            self.data_fname = pathlib.Path(data_fname)
        else:
            raise ValueError
        self.data = None

    def read_data(self):
        """Reads the json data located in self.data_fname into memory, to
        the attribute self.data.
        """
        self.data = pd.DataFrame(json.loads(self.data_fname.read_text()))

    def show_age_distrib(self) -> tuple[np.ndarray, np.ndarray]:
        """Calculates and plots the age distribution of the participants.

        Returns
        -------
        hist : np.ndarray
          Number of people in a given bin
        bins : np.ndarray
          Bin edges
        """
        age_data = pd.DataFrame(self.data).astype({'age':'float'}).sort_values("age")["age"]
        hist, bins = np.ndarray([10]), np.ndarray([11])
        i = 0
        for age_edge in range(0, 110, 10):
            bins[i] = age_edge
            bins_here = [age_edge, age_edge+9]
            if age_data.value_counts(bins=bins_here, dropna=True).values.size > 0 and i < 10:
                hist[i] = age_data.value_counts(bins=bins_here, dropna=True).values[0]
            elif i < 10:
                hist[i] = 0
            i += 1
        return hist, bins

    def remove_rows_without_mail(self) -> pd.DataFrame:
        """Checks self.data for rows with invalid emails, and removes them.

        Returns
        -------
        df : pd.DataFrame
        A corrected DataFrame, i.e. the same table but with the erroneous rows removed and
        the (ordinal) index after a reset.
        """
        df = pd.DataFrame(self.data)
        df = df[df.email.str.contains("@", na=False)]
        df = df[df.email.str.contains("\.", na=False)]
        df = df[~df.email.str.contains("@\.", na=False)]
        df = df[~df.email.str.startswith('@', na=False)]
        df = df[~df.email.str.startswith('\.', na=False)]
        df = df[df.email.str.count("@") == 1].reset_index(drop=True)
        return df

    def fill_na_with_mean(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """ Finds, in the original DataFrame, the subjects that didn't answer
        all questions, and replaces that missing value with the mean of the
        other grades for that student.

        Returns
        -------
        df : pd.DataFrame
          The corrected DataFrame after insertion of the mean grade
        arr : np.ndarray
              Row indices of the students that their new grades were generated
        """
        arr = np.array([])
        df = self.data.replace("nan", np.NaN)
        questions = ["q1", "q2", "q3", "q4", "q5"]
        for question in questions:
            mask = df[question].isna()
            arr = np.append(arr, df[mask].index)
            this_list = questions.copy()
            this_list.remove(question)
            for index in df[mask].index:
                df[question][index] = np.mean(df[this_list].iloc[index])
        df[questions] = df[questions].round(decimals=2)
        df.index = list(df.index)
        return df[["age","email","first_name","gender","id","last_name","q1","q2","q3","q4","q5"]], np.unique(sorted(arr))

    def score_subjects(self, maximal_nans_per_sub: int = 1) -> pd.DataFrame:
        """Calculates the average score of a subject and adds a new "score" column
        with it.

        If the subject has more than "maximal_nans_per_sub" NaN in his grades, the
        score should be NA. Otherwise, the score is simply the mean of the other grades.
        The datatype of score is UInt8, and the floating point raw numbers should be
        rounded down.

        Parameters
        ----------
        maximal_nans_per_sub : int, optional
            Number of allowed NaNs per subject before giving a NA score.

        Returns
        -------
        pd.DataFrame
            A new DF with a new column - "score".
        """
        df1 = pd.DataFrame(self.data).replace("nan", np.NaN)
        questions = ["q1", "q2", "q3", "q4", "q5"]
        df1["score"] = np.nanmean(df1[questions], axis=1)
        df1["score"] = df1["score"].apply(np.floor)
        df1['score'] = df1.apply(lambda row: pd.NA
                                 if row[questions].count() < (len(questions)-maximal_nans_per_sub)
                                 else row.score, axis=1)
        df1["score"] = df1["score"].astype('UInt8')
        return df1

    def correlate_gender_age(self) -> pd.DataFrame:
        """Looks for a correlation between the gender of the subject, their age
        and the score for all five questions.

        Returns
        -------
        pd.DataFrame
            A DataFrame with a MultiIndex containing the gender and whether the subject is above
            40 years of age, and the average score in each of the five questions.
        """
        questions = ["q1", "q2", "q3", "q4", "q5"]
        df1 = pd.DataFrame(self.data).replace("nan", np.nan)
        df1 = df1.dropna(subset=["age"]).reset_index(drop=True)
        df1["age"] = df1["age"].apply(lambda x: False if x < 40 else True)
        df1 = df1.set_index(['gender', 'age']).groupby(level=["gender", "age"]).mean()[questions].round(8)
        return df1
