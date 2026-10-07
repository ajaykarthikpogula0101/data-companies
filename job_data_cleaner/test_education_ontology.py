import unittest

from education_ontology import classify_education


class EducationOntologyTests(unittest.TestCase):
    def test_unrelated_training_abstains(self):
        result = classify_education("We provide extensive on-the-job training and mentorship.")
        self.assertEqual(result["education_type"].value, "")

    def test_explicit_vocational_requirement(self):
        result = classify_education("Required qualification: vocational training in electrical engineering.")
        self.assertEqual(result["education_type"].value, "Vocational Training")

    def test_apprenticeship_is_not_vocational(self):
        result = classify_education("Required qualification: completed apprenticeship as an electrician.")
        self.assertEqual(result["education_type"].value, "Apprenticeship")

    def test_high_school_is_not_bachelors_or_diploma(self):
        result = classify_education("Minimum education: high school diploma or GED.")
        self.assertEqual(result["education_type"].value, "Secondary / High School")

    def test_associate_precedes_bachelors_preference(self):
        result = classify_education("Associate degree required; bachelor's degree preferred.")
        self.assertEqual(result["education_type"].value, "Associate Degree")

    def test_type_does_not_invent_qualification(self):
        result = classify_education("A PhD is required.")
        self.assertEqual(result["education_type"].value, "Doctorate")
        self.assertEqual(result["education_qualification"].value, "")

    def test_ordinary_word_be_is_not_bachelors(self):
        result = classify_education("You will be responsible for customer support and training.")
        self.assertEqual(result["education_type"].value, "")
        self.assertEqual(result["education_qualification"].value, "")

    def test_dotted_uppercase_be_is_bachelors(self):
        result = classify_education("Required qualification: B.E. in Mechanical Engineering.")
        self.assertEqual(result["education_type"].value, "Bachelor's")


if __name__ == "__main__":
    unittest.main()
