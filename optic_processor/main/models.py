from django.db import models

# Create your models here.


class Answer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    book_type = models.CharField(max_length=10, null=True)
    exam_type  = models.CharField(max_length=10, null=True)
    turkish = models.CharField(max_length=100)
    maths = models.CharField(max_length=100)
    social_sciences = models.CharField(max_length=100)
    fen_sciences = models.CharField(max_length=100)

    class Meta:
        db_table = 'Answer'
        verbose_name = 'Answer'
        verbose_name_plural = 'Answers'

    def __str__(self):
        return f"{self.turkish}, {self.maths}, {self.social_sciences}, {self.fen_sciences}"





